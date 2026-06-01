from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .playlist_presets import PlaylistTrack
from .spotify import SpotifyClient, ensure_spotify_schema, log_operation, save_spotify_matches, upsert_spotify_playlist


@dataclass(frozen=True)
class DrumGrooveTrack:
    slot: int
    bucket: str
    artist: str
    title: str
    bpm: str
    bpm_source: str
    groove_fit: str
    tags: str
    lastfm_plays: str
    notes: str


@dataclass(frozen=True)
class DrumGroovePlaylist:
    name: str
    groove: str
    tracks: tuple[DrumGrooveTrack, ...]


def parse_verified_drum_grooves(path: Path) -> list[DrumGroovePlaylist]:
    playlists: list[DrumGroovePlaylist] = []
    current_name = ""
    current_groove = ""
    current_tracks: list[DrumGrooveTrack] = []
    in_table = False

    def flush() -> None:
        nonlocal current_tracks
        if current_name:
            playlists.append(DrumGroovePlaylist(current_name, current_groove, tuple(current_tracks)))
        current_tracks = []

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("## Drums Groove"):
            flush()
            current_name = line.removeprefix("## ").strip()
            current_groove = current_name.split(" - ", 1)[1] if " - " in current_name else current_name
            in_table = False
            continue
        if line.startswith("| Slot | Bucket |"):
            in_table = True
            continue
        if in_table and line.startswith("| ---"):
            continue
        if in_table and not line.startswith("|"):
            in_table = False
            continue
        if not in_table:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 11 or cells[4].casefold() != "yes":
            continue
        try:
            slot = int(cells[0])
        except ValueError:
            continue
        current_tracks.append(
            DrumGrooveTrack(
                slot=slot,
                bucket=cells[1],
                artist=cells[2],
                title=cells[3],
                bpm=cells[5],
                bpm_source=cells[6],
                groove_fit=cells[7],
                tags=cells[8],
                lastfm_plays=cells[9],
                notes=cells[10],
            )
        )
    flush()
    return playlists


def export_verified_drum_grooves_to_spotify(
    conn: sqlite3.Connection,
    client: SpotifyClient,
    markdown_path: Path,
    public: bool = False,
    delay_seconds: float = 10.0,
    limit: int | None = None,
    skip_existing: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    ensure_spotify_schema(conn)
    playlists = parse_verified_drum_grooves(markdown_path)
    if limit is not None:
        playlists = playlists[:limit]

    account = _sleep_then(delay_seconds, client.me)
    account_id = account["id"]
    existing_names = _existing_playlist_names(conn)
    if skip_existing:
        for playlist in _sleep_then(delay_seconds, client.list_playlists):
            existing_names.add(str(playlist.get("name", "")).casefold())

    created: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    missing_total = 0
    matched_total = 0

    for playlist in playlists:
        spotify_name = spotify_playlist_name(playlist)
        if skip_existing and spotify_name.casefold() in existing_names:
            skipped.append({"name": spotify_name, "reason": "already_exists"})
            log_operation(
                conn,
                "create_drum_groove_playlist",
                "playlist",
                "skipped_existing",
                target_name=spotify_name,
                details={"source": str(markdown_path), "track_count": len(playlist.tracks)},
            )
            continue

        matches: list[tuple[PlaylistTrack, dict[str, Any] | None]] = []
        uris: list[str] = []
        missing: list[dict[str, str]] = []
        for track in playlist.tracks:
            wanted = PlaylistTrack(track.artist, track.title)
            cached_uri = _cached_spotify_uri(conn, wanted)
            if cached_uri:
                uris.append(cached_uri)
                matched_total += 1
                continue
            match = _sleep_then(delay_seconds, client.search_track, wanted)
            matches.append((wanted, match))
            if match and match.get("uri"):
                uris.append(match["uri"])
                matched_total += 1
            else:
                missing.append({"artist": track.artist, "track": track.title})
                missing_total += 1
        if matches:
            save_spotify_matches(conn, matches)

        if dry_run:
            skipped.append({"name": spotify_name, "reason": "dry_run", "matched": len(uris), "missing": len(missing)})
            continue

        if not uris:
            skipped.append({"name": spotify_name, "reason": "no_matches"})
            log_operation(
                conn,
                "create_drum_groove_playlist",
                "playlist",
                "skipped_no_matches",
                target_name=spotify_name,
                details={"source": str(markdown_path), "missing": missing[:50]},
            )
            continue

        spotify_playlist = _sleep_then(delay_seconds, client.create_playlist, spotify_name, spotify_description(playlist), public)
        _sleep_then(delay_seconds, client.add_items, spotify_playlist["id"], uris)
        upsert_spotify_playlist(conn, account_id, spotify_playlist, created_by_app=True)
        log_operation(
            conn,
            "create_drum_groove_playlist",
            "playlist",
            "done",
            target_id=spotify_playlist["id"],
            target_name=spotify_name,
            details={
                "source": str(markdown_path),
                "tracks_total": len(playlist.tracks),
                "tracks_added": len(uris),
                "tracks_missing": len(missing),
                "missing": missing[:50],
            },
        )
        created.append(
            {
                "name": spotify_name,
                "id": spotify_playlist["id"],
                "url": spotify_playlist.get("external_urls", {}).get("spotify"),
                "tracks_added": len(uris),
                "tracks_missing": len(missing),
            }
        )
        existing_names.add(spotify_name.casefold())

    return {
        "playlists": len(playlists),
        "created": len(created),
        "skipped": len(skipped),
        "tracks_matched": matched_total,
        "tracks_missing": missing_total,
        "created_playlists": created,
        "skipped_playlists": skipped,
    }


def spotify_playlist_name(playlist: DrumGroovePlaylist) -> str:
    if playlist.name.startswith("Drums Groove "):
        suffix = playlist.name.removeprefix("Drums Groove ")
        return f"Drums: Grooves / {suffix}"
    return f"Drums: Grooves / {playlist.name}"


def spotify_description(playlist: DrumGroovePlaylist) -> str:
    styles = sorted({track.groove_fit for track in playlist.tracks if track.groove_fit})
    payload = {
        "groove": playlist.groove,
        "source": "Last.fm API App verified drum groove draft",
        "bpm_policy": "BPM values are practice approximations; verify before serious study.",
        "fits": styles[:5],
    }
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return text[:300]


def _cached_spotify_uri(conn: sqlite3.Connection, wanted: PlaylistTrack) -> str | None:
    row = conn.execute(
        "SELECT spotify_uri FROM spotify_track_matches WHERE artist_name = ? AND track_name = ?",
        (wanted.artist, wanted.track),
    ).fetchone()
    if row and row["spotify_uri"]:
        return str(row["spotify_uri"])
    return None


def _existing_playlist_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM spotify_playlists WHERE created_by_app = 1").fetchall()
    return {str(row["name"]).casefold() for row in rows}


def _sleep_then(delay_seconds: float, fn: Any, *args: Any, **kwargs: Any) -> Any:
    if delay_seconds > 0:
        time.sleep(delay_seconds)
    return fn(*args, **kwargs)
