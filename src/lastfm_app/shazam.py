from __future__ import annotations

import csv
import json
import os
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .config import load_dotenv
from .db import connect, normalize_name
from .playlist_presets import PlaylistTrack
from .spotify import SpotifyClient


DEFAULT_SHAZAM_DB_PATH = Path("data/shazam.sqlite3")
SHAZAM_RAPIDAPI_ROOT = "https://shazam.p.rapidapi.com"


class ShazamApiError(RuntimeError):
    pass


@dataclass(frozen=True)
class ShazamConfig:
    db_path: Path
    rapidapi_key: str | None = None
    rapidapi_host: str = "shazam.p.rapidapi.com"
    locale: str = "en-US"


def load_shazam_config() -> ShazamConfig:
    load_dotenv()
    return ShazamConfig(
        db_path=Path(os.environ.get("SHAZAM_DB_PATH", str(DEFAULT_SHAZAM_DB_PATH))).expanduser(),
        rapidapi_key=os.environ.get("SHAZAM_RAPIDAPI_KEY") or None,
        rapidapi_host=os.environ.get("SHAZAM_RAPIDAPI_HOST", "shazam.p.rapidapi.com"),
        locale=os.environ.get("SHAZAM_LOCALE", "en-US"),
    )


class ShazamApiClient:
    def __init__(self, config: ShazamConfig):
        if not config.rapidapi_key:
            raise ShazamApiError("SHAZAM_RAPIDAPI_KEY is required in .env for Shazam API calls.")
        self.config = config

    def search(self, term: str, limit: int = 5) -> list[dict[str, Any]]:
        params = urllib.parse.urlencode({"term": term, "locale": self.config.locale, "offset": "0", "limit": str(limit)})
        payload = self._request(f"{SHAZAM_RAPIDAPI_ROOT}/search?{params}")
        return _extract_shazam_hits(payload)

    def get_details(self, key: str) -> dict[str, Any]:
        params = urllib.parse.urlencode({"key": key, "locale": self.config.locale})
        return self._request(f"{SHAZAM_RAPIDAPI_ROOT}/songs/get-details?{params}")

    def _request(self, url: str) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "X-RapidAPI-Key": self.config.rapidapi_key or "",
                "X-RapidAPI-Host": self.config.rapidapi_host,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as error:
            raw = error.read().decode("utf-8", errors="replace")
            raise ShazamApiError(f"Shazam API HTTP {error.code}: {raw[:500]}") from error


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

        CREATE INDEX IF NOT EXISTS idx_shazam_tracks_norm ON shazam_tracks(normalized_artist_name, normalized_track_name);
        CREATE INDEX IF NOT EXISTS idx_shazam_tracks_energy ON shazam_tracks(energy_score, normalized_artist_name, normalized_track_name);
        CREATE INDEX IF NOT EXISTS idx_shazam_tracks_genre ON shazam_tracks(genre);
        """
    )
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


def import_shazam_api_search(conn: sqlite3.Connection, api_client: ShazamApiClient, query: str, limit: int = 5) -> dict[str, int]:
    ensure_shazam_schema(conn)
    run_id = _start_import_run(conn, Path(f"shazam-api-search:{query}"), "rapidapi-search")
    rows_seen = rows_inserted = rows_updated = 0
    try:
        for hit in api_client.search(query, limit=limit):
            rows_seen += 1
            parsed = parse_shazam_api_track(hit)
            if parsed is None:
                continue
            existed = upsert_shazam_track(conn, parsed, Path("shazam-api"))
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


def import_spotify_shazam_playlist(conn: sqlite3.Connection, spotify_client: SpotifyClient, playlist_id: str) -> dict[str, int]:
    ensure_shazam_schema(conn)
    run_id = _start_import_run(conn, Path(f"spotify-playlist:{playlist_id}"), "spotify-playlist-api")
    rows_seen = rows_inserted = rows_updated = 0
    try:
        for item in spotify_client.playlist_tracks(playlist_id):
            track = item.get("track") or {}
            if not track.get("name") or not track.get("artists"):
                continue
            rows_seen += 1
            parsed = parse_spotify_playlist_track(track, item.get("added_at"))
            existed = upsert_shazam_track(conn, parsed, Path(f"spotify-playlist:{playlist_id}"))
            _apply_spotify_match(conn, track, parsed)
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
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return [dict(row) for row in payload if isinstance(row, dict)]
        if isinstance(payload, dict):
            for key in ("tracks", "shazams", "items", "data"):
                if isinstance(payload.get(key), list):
                    return [dict(row) for row in payload[key] if isinstance(row, dict)]
            return [payload]
    raise ValueError(f"Unsupported Shazam import file: {path}. Use CSV or JSON.")


def parse_source_row(row: dict[str, Any]) -> dict[str, Any] | None:
    normalized = {_clean_key(key): value for key, value in row.items()}
    track_name = _first(normalized, "track title", "title", "track", "song", "name")
    artist_name = _first(normalized, "artist", "artist name", "subtitle", "primary artist")
    if not track_name or not artist_name:
        return None
    album_name = _first(normalized, "album", "album name", "release")
    shazamed_at = _first(normalized, "date shazamed", "shazamed at", "timestamp", "created at", "date")
    genre = _first(normalized, "genre", "genres", "primary genre")
    tags = parse_tags(_first(normalized, "tags", "tag", "genres", "moods") or "")
    if genre and genre not in tags:
        tags.insert(0, genre)
    return {
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


def parse_shazam_api_track(track: dict[str, Any]) -> dict[str, Any] | None:
    title = track.get("title") or track.get("heading", {}).get("title")
    subtitle = track.get("subtitle") or track.get("heading", {}).get("subtitle")
    if not title or not subtitle:
        return None
    sections = track.get("sections") or []
    metadata = _metadata_from_sections(sections)
    genres = track.get("genres") or {}
    genre = genres.get("primary") or metadata.get("Genre")
    return {
        "artist_name": str(subtitle).strip(),
        "track_name": str(title).strip(),
        "album_name": metadata.get("Album"),
        "shazamed_at": None,
        "genre": genre,
        "tags": parse_tags([genre] if genre else []),
        "shazam_url": track.get("url"),
        "apple_music_url": _apple_music_url(track),
        "source": track,
    }


def parse_spotify_playlist_track(track: dict[str, Any], added_at: str | None) -> dict[str, Any]:
    artists = track.get("artists") or []
    album = track.get("album") or {}
    artist_name = artists[0].get("name", "") if artists else ""
    tags = parse_tags([album.get("album_type") or ""])
    return {
        "artist_name": artist_name,
        "track_name": track.get("name", ""),
        "album_name": album.get("name"),
        "shazamed_at": added_at,
        "genre": None,
        "tags": tags,
        "shazam_url": None,
        "apple_music_url": None,
        "source": track,
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
    unique_key = "|".join([artist_norm, track_norm, parsed.get("shazamed_at") or ""])
    existed = conn.execute("SELECT 1 FROM shazam_tracks WHERE unique_key = ?", (unique_key,)).fetchone() is not None
    energy_score = score_energy(parsed.get("genre"), parsed.get("tags") or [])
    conn.execute(
        """
        INSERT INTO shazam_tracks(
          unique_key, artist_name, track_name, normalized_artist_name, normalized_track_name, album_name, shazamed_at,
          genre, tags_json, shazam_url, apple_music_url, energy_score, source_path, source_json
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(unique_key) DO UPDATE SET
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


def generate_shazam_playlists(conn: sqlite3.Connection) -> dict[str, int]:
    ensure_shazam_schema(conn)
    conn.execute("DELETE FROM shazam_playlist_items")
    conn.execute("DELETE FROM shazam_playlists")
    rows = conn.execute(
        """
        SELECT *
        FROM shazam_tracks
        ORDER BY energy_score ASC, COALESCE(genre, ''), normalized_artist_name, normalized_track_name
        """
    ).fetchall()
    if not rows:
        conn.commit()
        return {"playlists": 0, "items": 0}
    total_items = _create_playlist(
        conn,
        name="All Shazams: Calm To Energetic",
        kind="all_energy",
        rows=rows,
        description="Every imported Shazam track sorted from the calmest to the most energetic.",
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
    return "other"


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


def _genre_buckets(rows: list[sqlite3.Row]) -> dict[str, list[sqlite3.Row]]:
    buckets: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        buckets.setdefault(bucket_for_track(row), []).append(row)
    return {bucket: sorted(items, key=lambda row: (row["energy_score"], row["normalized_artist_name"], row["normalized_track_name"])) for bucket, items in sorted(buckets.items())}


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


def _start_import_run(conn: sqlite3.Connection, path: Path, source_type: str) -> int:
    cursor = conn.execute(
        "INSERT INTO shazam_import_runs(source_path, source_type, status) VALUES(?, ?, 'running')",
        (str(path), source_type),
    )
    conn.commit()
    return int(cursor.lastrowid)


def _extract_shazam_hits(payload: dict[str, Any]) -> list[dict[str, Any]]:
    tracks = payload.get("tracks")
    if isinstance(tracks, dict):
        hits = tracks.get("hits") or []
    else:
        hits = payload.get("hits") or []
    result: list[dict[str, Any]] = []
    for hit in hits:
        if not isinstance(hit, dict):
            continue
        track = hit.get("track") if isinstance(hit.get("track"), dict) else hit
        if isinstance(track, dict):
            result.append(track)
    return result


def _metadata_from_sections(sections: list[dict[str, Any]]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for section in sections:
        for item in section.get("metadata") or []:
            title = item.get("title")
            text = item.get("text")
            if title and text:
                metadata[str(title)] = str(text)
    return metadata


def _apple_music_url(track: dict[str, Any]) -> str | None:
    for hub_action in track.get("hub", {}).get("actions") or []:
        uri = hub_action.get("uri")
        if isinstance(uri, str) and "music.apple.com" in uri:
            return uri
    return None


def _apply_spotify_match(conn: sqlite3.Connection, spotify_track: dict[str, Any], parsed: dict[str, Any]) -> None:
    unique_key = "|".join(
        [
            normalize_name(parsed["artist_name"]),
            normalize_name(parsed["track_name"]),
            parsed.get("shazamed_at") or "",
        ]
    )
    conn.execute(
        """
        UPDATE shazam_tracks
        SET spotify_track_id=?, spotify_uri=?, spotify_url=?, spotify_popularity=?, updated_at=CURRENT_TIMESTAMP
        WHERE unique_key=?
        """,
        (
            spotify_track.get("id"),
            spotify_track.get("uri"),
            spotify_track.get("external_urls", {}).get("spotify"),
            spotify_track.get("popularity"),
            unique_key,
        ),
    )


def _clean_key(key: str) -> str:
    return " ".join(str(key).strip().casefold().replace("_", " ").replace("-", " ").split())


def _first(row: dict[str, Any], *keys: str) -> Any | None:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None
