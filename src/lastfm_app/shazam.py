from __future__ import annotations

import csv
import json
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .config import load_dotenv
from .db import connect, normalize_name
from .playlist_presets import PlaylistTrack
from .spotify import SpotifyClient


DEFAULT_SHAZAM_DB_PATH = Path("data/shazam.sqlite3")


@dataclass(frozen=True)
class ShazamConfig:
    db_path: Path


def load_shazam_config() -> ShazamConfig:
    load_dotenv()
    return ShazamConfig(db_path=Path(os.environ.get("SHAZAM_DB_PATH", str(DEFAULT_SHAZAM_DB_PATH))).expanduser())


def connect_shazam(db_path: Path | None = None) -> sqlite3.Connection:
    return connect(db_path or load_shazam_config().db_path)


def ensure_shazam_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS shazam_import_runs (
          id INTEGER PRIMARY KEY,
          source_path TEXT NOT NULL,
          source_type TEXT NOT NULL,
          started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          finished_at TEXT,
          status TEXT NOT NULL,
          rows_seen INTEGER NOT NULL DEFAULT 0,
          rows_inserted INTEGER NOT NULL DEFAULT 0,
          rows_updated INTEGER NOT NULL DEFAULT 0,
          error TEXT
        );

        CREATE TABLE IF NOT EXISTS shazam_tracks (
          id INTEGER PRIMARY KEY,
          unique_key TEXT NOT NULL UNIQUE,
          source_index INTEGER,
          shazam_track_key TEXT,
          artist_name TEXT NOT NULL,
          track_name TEXT NOT NULL,
          normalized_artist_name TEXT NOT NULL,
          normalized_track_name TEXT NOT NULL,
          album_name TEXT,
          shazamed_at TEXT,
          genre TEXT,
          tags_json TEXT,
          shazam_url TEXT,
          apple_music_url TEXT,
          spotify_track_id TEXT,
          spotify_uri TEXT,
          spotify_url TEXT,
          spotify_popularity INTEGER,
          lastfm_track_id INTEGER,
          energy_score INTEGER NOT NULL DEFAULT 50,
          source_path TEXT,
          source_json TEXT,
          first_imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS shazam_playlists (
          id INTEGER PRIMARY KEY,
          name TEXT NOT NULL,
          kind TEXT NOT NULL,
          description TEXT,
          vibe TEXT,
          tags_json TEXT,
          generated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS shazam_playlist_items (
          playlist_id INTEGER NOT NULL REFERENCES shazam_playlists(id) ON DELETE CASCADE,
          shazam_track_id INTEGER NOT NULL REFERENCES shazam_tracks(id) ON DELETE CASCADE,
          position INTEGER NOT NULL,
          energy_score INTEGER NOT NULL,
          PRIMARY KEY(playlist_id, position)
        );

        CREATE TABLE IF NOT EXISTS shazam_spotify_playlist_exports (
          id INTEGER PRIMARY KEY,
          shazam_playlist_id INTEGER NOT NULL REFERENCES shazam_playlists(id) ON DELETE CASCADE,
          shazam_playlist_name TEXT NOT NULL,
          spotify_playlist_id TEXT,
          spotify_uri TEXT,
          spotify_url TEXT,
          spotify_name TEXT NOT NULL,
          status TEXT NOT NULL,
          tracks_total INTEGER NOT NULL,
          tracks_matched INTEGER NOT NULL,
          tracks_added INTEGER NOT NULL,
          tracks_missing INTEGER NOT NULL,
          details_json TEXT,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_shazam_tracks_norm ON shazam_tracks(normalized_artist_name, normalized_track_name);
        CREATE INDEX IF NOT EXISTS idx_shazam_tracks_energy ON shazam_tracks(energy_score, normalized_artist_name, normalized_track_name);
        CREATE INDEX IF NOT EXISTS idx_shazam_tracks_genre ON shazam_tracks(genre);
        CREATE INDEX IF NOT EXISTS idx_shazam_exports_playlist ON shazam_spotify_playlist_exports(shazam_playlist_id, created_at);
        """
    )
    _ensure_column(conn, "shazam_tracks", "source_index", "INTEGER")
    _ensure_column(conn, "shazam_tracks", "shazam_track_key", "TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_shazam_tracks_track_key ON shazam_tracks(shazam_track_key)")
    conn.commit()


def import_shazam_file(conn: sqlite3.Connection, path: Path) -> dict[str, int]:
    ensure_shazam_schema(conn)
    source_type = path.suffix.lower().lstrip(".") or "unknown"
    run_id = _start_import_run(conn, path, source_type)
    rows_seen = rows_inserted = rows_updated = 0
    try:
        for row in read_source_rows(path):
            rows_seen += 1
            parsed = parse_source_row(row)
            if parsed is None:
                continue
            existed = upsert_shazam_track(conn, parsed, path)
            if existed:
                rows_updated += 1
            else:
                rows_inserted += 1
        conn.execute(
            """
            UPDATE shazam_import_runs
            SET finished_at=CURRENT_TIMESTAMP, status='done', rows_seen=?, rows_inserted=?, rows_updated=?
            WHERE id=?
            """,
            (rows_seen, rows_inserted, rows_updated, run_id),
        )
        conn.commit()
    except Exception as error:
        conn.execute(
            "UPDATE shazam_import_runs SET finished_at=CURRENT_TIMESTAMP, status='failed', error=? WHERE id=?",
            (str(error), run_id),
        )
        conn.commit()
        raise
    return {"rows_seen": rows_seen, "rows_inserted": rows_inserted, "rows_updated": rows_updated}


def read_source_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return read_csv_rows(path)
    raise ValueError(f"Unsupported Shazam import file: {path}. Use the CSV downloaded from Shazam on the web.")


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    header_index = 0
    for index, line in enumerate(lines):
        normalized = line.strip().casefold()
        if normalized.startswith("index,") or "tagtime" in normalized and "title" in normalized and "artist" in normalized:
            header_index = index
            break
    csv_text = "\n".join(lines[header_index:])
    return [dict(row) for row in csv.DictReader(csv_text.splitlines())]


def parse_source_row(row: dict[str, Any]) -> dict[str, Any] | None:
    normalized = {_clean_key(key): value for key, value in row.items()}
    track_name = _first(normalized, "track title", "title", "track", "song", "name")
    artist_name = _first(normalized, "artist", "artist name", "subtitle", "primary artist")
    if not track_name or not artist_name:
        return None
    album_name = _first(normalized, "album", "album name", "release")
    shazamed_at = _first(normalized, "tagtime", "date shazamed", "shazamed at", "timestamp", "created at", "date")
    genre = _first(normalized, "genre", "genres", "primary genre")
    tags = parse_tags(_first(normalized, "tags", "tag", "genres", "moods") or "")
    if genre and genre not in tags:
        tags.insert(0, genre)
    return {
        "source_index": _int_or_none(_first(normalized, "index")),
        "shazam_track_key": str(_first(normalized, "trackkey", "track key", "shazam track key") or "").strip() or None,
        "artist_name": str(artist_name).strip(),
        "track_name": str(track_name).strip(),
        "album_name": str(album_name).strip() if album_name else None,
        "shazamed_at": str(shazamed_at).strip() if shazamed_at else None,
        "genre": str(genre).strip() if genre else None,
        "tags": tags,
        "shazam_url": _first(normalized, "shazam url", "url", "web url"),
        "apple_music_url": _first(normalized, "apple music url", "apple url", "music url"),
        "source": row,
    }


def parse_tags(value: str | Iterable[str]) -> list[str]:
    if isinstance(value, str):
        parts = value.replace("|", ",").replace(";", ",").split(",")
    else:
        parts = list(value)
    tags: list[str] = []
    seen: set[str] = set()
    for part in parts:
        tag = str(part).strip()
        norm = normalize_name(tag)
        if tag and norm not in seen:
            tags.append(tag)
            seen.add(norm)
    return tags


def upsert_shazam_track(conn: sqlite3.Connection, parsed: dict[str, Any], source_path: Path) -> bool:
    artist_norm = normalize_name(parsed["artist_name"])
    track_norm = normalize_name(parsed["track_name"])
    shazam_track_key = parsed.get("shazam_track_key")
    unique_key = f"shazam:{shazam_track_key}" if shazam_track_key else "|".join([artist_norm, track_norm, parsed.get("shazamed_at") or ""])
    existed = conn.execute("SELECT 1 FROM shazam_tracks WHERE unique_key = ?", (unique_key,)).fetchone() is not None
    energy_score = score_energy(parsed.get("genre"), parsed.get("tags") or [])
    conn.execute(
        """
        INSERT INTO shazam_tracks(
          unique_key, source_index, shazam_track_key, artist_name, track_name, normalized_artist_name, normalized_track_name, album_name, shazamed_at,
          genre, tags_json, shazam_url, apple_music_url, energy_score, source_path, source_json
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(unique_key) DO UPDATE SET
          source_index=COALESCE(excluded.source_index, shazam_tracks.source_index),
          shazam_track_key=COALESCE(excluded.shazam_track_key, shazam_tracks.shazam_track_key),
          album_name=COALESCE(excluded.album_name, shazam_tracks.album_name),
          genre=COALESCE(excluded.genre, shazam_tracks.genre),
          tags_json=excluded.tags_json,
          shazam_url=COALESCE(excluded.shazam_url, shazam_tracks.shazam_url),
          apple_music_url=COALESCE(excluded.apple_music_url, shazam_tracks.apple_music_url),
          energy_score=excluded.energy_score,
          source_path=excluded.source_path,
          source_json=excluded.source_json,
          updated_at=CURRENT_TIMESTAMP
        """,
        (
            unique_key,
            parsed.get("source_index"),
            shazam_track_key,
            parsed["artist_name"],
            parsed["track_name"],
            artist_norm,
            track_norm,
            parsed.get("album_name"),
            parsed.get("shazamed_at"),
            parsed.get("genre"),
            json.dumps(parsed.get("tags") or [], ensure_ascii=False),
            parsed.get("shazam_url"),
            parsed.get("apple_music_url"),
            energy_score,
            str(source_path),
            json.dumps(parsed.get("source") or {}, ensure_ascii=False, sort_keys=True),
        ),
    )
    conn.commit()
    return existed


def link_lastfm_tracks(shazam_conn: sqlite3.Connection, lastfm_conn: sqlite3.Connection) -> int:
    ensure_shazam_schema(shazam_conn)
    rows = shazam_conn.execute(
        "SELECT id, normalized_artist_name, normalized_track_name FROM shazam_tracks WHERE lastfm_track_id IS NULL"
    ).fetchall()
    linked = 0
    for row in rows:
        match = lastfm_conn.execute(
            """
            SELECT t.id
            FROM tracks t
            JOIN artists a ON a.id = t.artist_id
            WHERE a.normalized_name = ? AND t.normalized_name = ?
            """,
            (row["normalized_artist_name"], row["normalized_track_name"]),
        ).fetchone()
        if match:
            shazam_conn.execute("UPDATE shazam_tracks SET lastfm_track_id=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (match["id"], row["id"]))
            linked += 1
    shazam_conn.commit()
    return linked


def enrich_from_lastfm(shazam_conn: sqlite3.Connection, lastfm_conn: sqlite3.Connection) -> int:
    ensure_shazam_schema(shazam_conn)
    rows = shazam_conn.execute("SELECT id, lastfm_track_id FROM shazam_tracks WHERE lastfm_track_id IS NOT NULL").fetchall()
    enriched = 0
    for row in rows:
        tags = _lastfm_tags_for_track(lastfm_conn, int(row["lastfm_track_id"]))
        if not tags:
            continue
        genre = tags[0]
        shazam_conn.execute(
            """
            UPDATE shazam_tracks
            SET genre=?, tags_json=?, energy_score=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (genre, json.dumps(tags, ensure_ascii=False), score_energy(genre, tags), row["id"]),
        )
        enriched += 1
    shazam_conn.commit()
    return enriched


def match_spotify_tracks(conn: sqlite3.Connection, client: SpotifyClient, limit: int | None = None) -> dict[str, int]:
    ensure_shazam_schema(conn)
    query = """
        SELECT id, artist_name, track_name
        FROM shazam_tracks
        WHERE spotify_track_id IS NULL
        ORDER BY shazamed_at DESC, id DESC
    """
    if limit is not None:
        query += " LIMIT ?"
        rows = conn.execute(query, (limit,)).fetchall()
    else:
        rows = conn.execute(query).fetchall()
    matched = 0
    for row in rows:
        match = client.search_track(PlaylistTrack(artist=row["artist_name"], track=row["track_name"]))
        if not match:
            continue
        conn.execute(
            """
            UPDATE shazam_tracks
            SET spotify_track_id=?, spotify_uri=?, spotify_url=?, spotify_popularity=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                match.get("id"),
                match.get("uri"),
                match.get("external_urls", {}).get("spotify"),
                match.get("popularity"),
                row["id"],
            ),
        )
        matched += 1
    conn.commit()
    return {"checked": len(rows), "matched": matched}


def export_shazam_playlists_to_spotify(
    conn: sqlite3.Connection,
    client: SpotifyClient,
    public: bool = False,
    match_missing: bool = True,
    request_delay_seconds: float = 0.0,
) -> dict[str, int]:
    ensure_shazam_schema(conn)
    playlists = conn.execute("SELECT id, name, description, vibe FROM shazam_playlists ORDER BY id").fetchall()
    if not playlists:
        generate_shazam_playlists(conn)
        playlists = conn.execute("SELECT id, name, description, vibe FROM shazam_playlists ORDER BY id").fetchall()
    exported = 0
    total_added = 0
    total_missing = 0
    for playlist in playlists:
        rows = conn.execute(
            """
            SELECT s.id, s.artist_name, s.track_name, s.spotify_uri
            FROM shazam_playlist_items i
            JOIN shazam_tracks s ON s.id = i.shazam_track_id
            WHERE i.playlist_id = ?
            ORDER BY i.position
            """,
            (playlist["id"],),
        ).fetchall()
        uris: list[str] = []
        missing: list[dict[str, Any]] = []
        for row in rows:
            uri = row["spotify_uri"]
            if not uri and match_missing:
                uri = _match_one_spotify_track(conn, client, row)
            if uri:
                uris.append(uri)
            else:
                missing.append({"artist": row["artist_name"], "track": row["track_name"], "shazam_track_id": row["id"]})
        spotify_name = _spotify_playlist_name(playlist["name"])
        description = _spotify_playlist_description(playlist["description"], playlist["vibe"])
        status = "skipped_no_matches"
        spotify_playlist: dict[str, Any] | None = None
        if uris:
            _sleep_before_spotify_request(request_delay_seconds)
            spotify_playlist = client.create_playlist(spotify_name, description, public=public)
            _sleep_before_spotify_request(request_delay_seconds)
            client.add_items(spotify_playlist["id"], uris)
            status = "created"
            exported += 1
            total_added += len(uris)
        total_missing += len(missing)
        conn.execute(
            """
            INSERT INTO shazam_spotify_playlist_exports(
              shazam_playlist_id, shazam_playlist_name, spotify_playlist_id, spotify_uri, spotify_url, spotify_name,
              status, tracks_total, tracks_matched, tracks_added, tracks_missing, details_json
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                playlist["id"],
                playlist["name"],
                spotify_playlist.get("id") if spotify_playlist else None,
                spotify_playlist.get("uri") if spotify_playlist else None,
                spotify_playlist.get("external_urls", {}).get("spotify") if spotify_playlist else None,
                spotify_name,
                status,
                len(rows),
                len(uris),
                len(uris),
                len(missing),
                json.dumps({"missing": missing[:50]}, ensure_ascii=False, sort_keys=True),
            ),
        )
        conn.commit()
    return {"playlists": len(playlists), "exported": exported, "tracks_added": total_added, "tracks_missing": total_missing}


def spotify_export_report(conn: sqlite3.Connection, limit: int = 20) -> str:
    ensure_shazam_schema(conn)
    rows = conn.execute(
        """
        SELECT shazam_playlist_name, spotify_name, spotify_url, status, tracks_added, tracks_missing, created_at
        FROM shazam_spotify_playlist_exports
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    if not rows:
        return "No Shazam Spotify exports recorded yet."
    lines = ["# Shazam Spotify Exports", ""]
    for row in rows:
        url = f" / {row['spotify_url']}" if row["spotify_url"] else ""
        lines.append(
            f"- {row['created_at']} | {row['status']} | {row['spotify_name']} | "
            f"added={row['tracks_added']} missing={row['tracks_missing']}{url}"
        )
    return "\n".join(lines)


def generate_shazam_playlists(conn: sqlite3.Connection) -> dict[str, int]:
    ensure_shazam_schema(conn)
    conn.execute("DELETE FROM shazam_playlist_items")
    conn.execute("DELETE FROM shazam_playlists")
    rows = conn.execute(
        """
        SELECT *
        FROM shazam_tracks
        ORDER BY energy_score DESC, COALESCE(genre, ''), normalized_artist_name, normalized_track_name
        """
    ).fetchall()
    if not rows:
        conn.commit()
        return {"playlists": 0, "items": 0}
    total_items = _create_playlist(
        conn,
        name="Shazam: Energy High To Low",
        kind="all_energy_desc",
        rows=rows,
        description="Every imported Shazam track sorted from the most energetic to the least energetic.",
    )
    for bucket, bucket_rows in _genre_buckets(rows).items():
        _create_playlist(
            conn,
            name=f"Shazam: {bucket.title()}",
            kind=f"genre:{bucket}",
            rows=bucket_rows,
            description=f"Imported Shazam tracks grouped under {bucket}.",
        )
        total_items += len(bucket_rows)
    conn.commit()
    playlist_count = conn.execute("SELECT COUNT(*) AS count FROM shazam_playlists").fetchone()["count"]
    return {"playlists": int(playlist_count), "items": total_items}


def playlist_report(conn: sqlite3.Connection, limit: int | None = None) -> str:
    ensure_shazam_schema(conn)
    playlists = conn.execute("SELECT id, name, kind, description FROM shazam_playlists ORDER BY id").fetchall()
    if not playlists:
        return "No Shazam playlists generated yet. Import Shazam tracks first, then run: lastfm-app shazam playlists --show"
    lines = ["# Shazam Playlists", ""]
    for playlist in playlists:
        lines.append(f"## {playlist['name']}")
        lines.append(playlist["description"] or "")
        item_query = """
            SELECT s.artist_name, s.track_name, s.genre, s.energy_score
            FROM shazam_playlist_items i
            JOIN shazam_tracks s ON s.id = i.shazam_track_id
            WHERE i.playlist_id = ?
            ORDER BY i.position
        """
        if limit is not None:
            item_query += " LIMIT ?"
            items = conn.execute(item_query, (playlist["id"], limit)).fetchall()
        else:
            items = conn.execute(item_query, (playlist["id"],)).fetchall()
        for idx, item in enumerate(items, start=1):
            genre = f" / {item['genre']}" if item["genre"] else ""
            lines.append(f"{idx}. {item['artist_name']} - {item['track_name']} [{item['energy_score']}/100{genre}]")
        lines.append("")
    return "\n".join(lines).strip()


def shazam_status(conn: sqlite3.Connection) -> str:
    ensure_shazam_schema(conn)
    tracks = conn.execute("SELECT COUNT(*) AS count FROM shazam_tracks").fetchone()["count"]
    spotify = conn.execute("SELECT COUNT(*) AS count FROM shazam_tracks WHERE spotify_track_id IS NOT NULL").fetchone()["count"]
    lastfm = conn.execute("SELECT COUNT(*) AS count FROM shazam_tracks WHERE lastfm_track_id IS NOT NULL").fetchone()["count"]
    playlists = conn.execute("SELECT COUNT(*) AS count FROM shazam_playlists").fetchone()["count"]
    lines = [
        "# Shazam Status",
        "",
        f"- tracks: {tracks}",
        f"- spotify matches: {spotify}",
        f"- lastfm links: {lastfm}",
        f"- generated playlists: {playlists}",
    ]
    return "\n".join(lines)


def score_energy(genre: str | None, tags: Iterable[str]) -> int:
    text = " ".join([genre or "", *tags]).casefold()
    score = 50
    weights = {
        "ambient": -28,
        "classical": -25,
        "acoustic": -22,
        "chill": -20,
        "downtempo": -18,
        "soul": -8,
        "jazz": -8,
        "folk": -10,
        "indie": 2,
        "pop": 5,
        "house": 14,
        "electronic": 14,
        "dance": 16,
        "rock": 16,
        "techno": 22,
        "punk": 22,
        "metal": 25,
        "drum and bass": 26,
        "dnb": 26,
        "hardcore": 28,
    }
    for needle, weight in weights.items():
        if needle in text:
            score += weight
    return max(0, min(100, score))


def bucket_for_track(row: sqlite3.Row) -> str:
    tags = [row["genre"] or "", *json.loads(row["tags_json"] or "[]")]
    text = " ".join(tags).casefold()
    buckets = [
        ("ambient-chill", ("ambient", "chill", "downtempo", "lo-fi", "lounge")),
        ("electronic", ("electronic", "house", "techno", "dance", "edm", "dnb", "drum and bass", "trance")),
        ("rock", ("rock", "alternative", "indie rock", "garage")),
        ("metal-punk", ("metal", "punk", "hardcore", "grunge")),
        ("hip-hop", ("hip hop", "hip-hop", "rap", "trap")),
        ("pop", ("pop", "synthpop", "electropop")),
        ("jazz-soul-funk", ("jazz", "soul", "funk", "r&b", "blues")),
        ("folk-acoustic", ("folk", "acoustic", "singer-songwriter", "country")),
        ("latin-world", ("latin", "reggae", "afro", "world")),
    ]
    for bucket, needles in buckets:
        if any(needle in text for needle in needles):
            return bucket
    return "various"


def _create_playlist(conn: sqlite3.Connection, name: str, kind: str, rows: list[sqlite3.Row], description: str) -> int:
    vibe = _vibe_for_rows(rows)
    tags = sorted({bucket_for_track(row) for row in rows})
    cursor = conn.execute(
        "INSERT INTO shazam_playlists(name, kind, description, vibe, tags_json) VALUES(?, ?, ?, ?, ?)",
        (name, kind, description, vibe, json.dumps(tags, ensure_ascii=False)),
    )
    playlist_id = int(cursor.lastrowid)
    for position, row in enumerate(rows, start=1):
        conn.execute(
            "INSERT INTO shazam_playlist_items(playlist_id, shazam_track_id, position, energy_score) VALUES(?, ?, ?, ?)",
            (playlist_id, row["id"], position, row["energy_score"]),
        )
    return len(rows)


def _match_one_spotify_track(conn: sqlite3.Connection, client: SpotifyClient, row: sqlite3.Row) -> str | None:
    match = client.search_track(PlaylistTrack(artist=row["artist_name"], track=row["track_name"]))
    if not match:
        return None
    conn.execute(
        """
        UPDATE shazam_tracks
        SET spotify_track_id=?, spotify_uri=?, spotify_url=?, spotify_popularity=?, updated_at=CURRENT_TIMESTAMP
        WHERE id=?
        """,
        (
            match.get("id"),
            match.get("uri"),
            match.get("external_urls", {}).get("spotify"),
            match.get("popularity"),
            row["id"],
        ),
    )
    conn.commit()
    return match.get("uri")


def _spotify_playlist_name(name: str) -> str:
    return name.replace("Shazam: Various", "Shazam: Various / Unknown")


def _spotify_playlist_description(description: str | None, vibe: str | None) -> str:
    parts = [description or "Generated from local Shazam library."]
    if vibe:
        parts.append(f"Vibe: {vibe}.")
    parts.append("Generated by lastFmApiApp from Shazam CSV.")
    return " ".join(parts)[:300]


def _sleep_before_spotify_request(delay_seconds: float) -> None:
    if delay_seconds > 0:
        time.sleep(delay_seconds)


def _genre_buckets(rows: list[sqlite3.Row]) -> dict[str, list[sqlite3.Row]]:
    buckets: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        buckets.setdefault(bucket_for_track(row), []).append(row)
    return {
        bucket: sorted(items, key=lambda row: (-int(row["energy_score"]), row["normalized_artist_name"], row["normalized_track_name"]))
        for bucket, items in sorted(buckets.items())
    }


def _vibe_for_rows(rows: list[sqlite3.Row]) -> str:
    if not rows:
        return "empty"
    average = sum(int(row["energy_score"]) for row in rows) / len(rows)
    if average < 35:
        return "calm, low-pressure, speaker-friendly"
    if average < 60:
        return "balanced, melodic, mid-energy"
    if average < 78:
        return "upbeat, driving, high-energy"
    return "very energetic, intense, peak-time"


def _lastfm_tags_for_track(conn: sqlite3.Connection, track_id: int) -> list[str]:
    track_tags = conn.execute(
        """
        SELECT tg.name, COALESCE(tt.weight, 0) AS weight
        FROM track_tags tt
        JOIN tags tg ON tg.id = tt.tag_id
        WHERE tt.track_id = ?
        ORDER BY weight DESC, tg.name COLLATE NOCASE
        LIMIT 8
        """,
        (track_id,),
    ).fetchall()
    artist_tags = conn.execute(
        """
        SELECT tg.name, COALESCE(at.weight, 0) AS weight
        FROM tracks tr
        JOIN artist_tags at ON at.artist_id = tr.artist_id
        JOIN tags tg ON tg.id = at.tag_id
        WHERE tr.id = ?
        ORDER BY weight DESC, tg.name COLLATE NOCASE
        LIMIT 8
        """,
        (track_id,),
    ).fetchall()
    tags: list[str] = []
    seen: set[str] = set()
    for row in [*track_tags, *artist_tags]:
        tag = row["name"]
        normalized = normalize_name(tag)
        if normalized not in seen:
            tags.append(tag)
            seen.add(normalized)
    return tags[:10]


def _start_import_run(conn: sqlite3.Connection, path: Path, source_type: str) -> int:
    cursor = conn.execute(
        "INSERT INTO shazam_import_runs(source_path, source_type, status) VALUES(?, ?, 'running')",
        (str(path), source_type),
    )
    conn.commit()
    return int(cursor.lastrowid)


def _clean_key(key: str) -> str:
    return " ".join(str(key).strip().casefold().replace("_", " ").replace("-", " ").split())


def _first(row: dict[str, Any], *keys: str) -> Any | None:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def _int_or_none(value: Any | None) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(str(value))
    except ValueError:
        return None


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
