from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_meta (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS artists (
          id INTEGER PRIMARY KEY,
          name TEXT NOT NULL UNIQUE,
          normalized_name TEXT NOT NULL,
          mbid TEXT,
          url TEXT,
          listeners INTEGER,
          global_playcount INTEGER,
          bio_summary TEXT,
          first_seen TEXT,
          last_seen TEXT,
          raw_json TEXT,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS albums (
          id INTEGER PRIMARY KEY,
          artist_id INTEGER NOT NULL REFERENCES artists(id),
          name TEXT NOT NULL,
          normalized_name TEXT NOT NULL,
          mbid TEXT,
          url TEXT,
          first_seen TEXT,
          last_seen TEXT,
          raw_json TEXT,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(artist_id, normalized_name)
        );

        CREATE TABLE IF NOT EXISTS tracks (
          id INTEGER PRIMARY KEY,
          artist_id INTEGER NOT NULL REFERENCES artists(id),
          album_id INTEGER REFERENCES albums(id),
          name TEXT NOT NULL,
          normalized_name TEXT NOT NULL,
          mbid TEXT,
          duration_ms INTEGER,
          url TEXT,
          loved INTEGER,
          first_seen TEXT,
          last_seen TEXT,
          raw_json TEXT,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(artist_id, normalized_name)
        );

        CREATE TABLE IF NOT EXISTS scrobbles (
          id INTEGER PRIMARY KEY,
          track_id INTEGER NOT NULL REFERENCES tracks(id),
          played_at_utc TEXT NOT NULL,
          source TEXT NOT NULL DEFAULT 'user.getRecentTracks',
          raw_artist_name TEXT NOT NULL,
          raw_track_name TEXT NOT NULL,
          raw_album_name TEXT,
          raw_json TEXT,
          imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(track_id, played_at_utc)
        );

        CREATE TABLE IF NOT EXISTS tags (
          id INTEGER PRIMARY KEY,
          name TEXT NOT NULL UNIQUE,
          normalized_name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS artist_tags (
          artist_id INTEGER NOT NULL REFERENCES artists(id) ON DELETE CASCADE,
          tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
          weight INTEGER,
          source TEXT NOT NULL,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY(artist_id, tag_id, source)
        );

        CREATE TABLE IF NOT EXISTS track_tags (
          track_id INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
          tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
          weight INTEGER,
          source TEXT NOT NULL,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY(track_id, tag_id, source)
        );

        CREATE TABLE IF NOT EXISTS user_artist_stats (
          artist_id INTEGER PRIMARY KEY REFERENCES artists(id) ON DELETE CASCADE,
          playcount INTEGER NOT NULL,
          first_played_at TEXT,
          last_played_at TEXT,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS user_track_stats (
          track_id INTEGER PRIMARY KEY REFERENCES tracks(id) ON DELETE CASCADE,
          playcount INTEGER NOT NULL,
          first_played_at TEXT,
          last_played_at TEXT,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS user_album_stats (
          album_id INTEGER PRIMARY KEY REFERENCES albums(id) ON DELETE CASCADE,
          playcount INTEGER NOT NULL,
          first_played_at TEXT,
          last_played_at TEXT,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS api_cache (
          method TEXT NOT NULL,
          params_hash TEXT NOT NULL,
          params_json TEXT NOT NULL,
          response_json TEXT NOT NULL,
          fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          status TEXT NOT NULL DEFAULT 'ok',
          PRIMARY KEY(method, params_hash)
        );

        CREATE TABLE IF NOT EXISTS import_runs (
          id INTEGER PRIMARY KEY,
          command TEXT NOT NULL,
          started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          finished_at TEXT,
          status TEXT NOT NULL,
          pages_fetched INTEGER NOT NULL DEFAULT 0,
          rows_inserted INTEGER NOT NULL DEFAULT 0,
          error TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_scrobbles_played_at ON scrobbles(played_at_utc);
        CREATE INDEX IF NOT EXISTS idx_tracks_artist ON tracks(artist_id);
        CREATE INDEX IF NOT EXISTS idx_albums_artist ON albums(artist_id);
        """
    )
    conn.execute(
        "INSERT OR REPLACE INTO schema_meta(key, value) VALUES('schema_version', ?)",
        (str(SCHEMA_VERSION),),
    )
    conn.commit()


def normalize_name(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def upsert_artist(conn: sqlite3.Connection, name: str, **fields: Any) -> int:
    normalized = normalize_name(name)
    conn.execute(
        """
        INSERT INTO artists(name, normalized_name, mbid, url, listeners, global_playcount, bio_summary, raw_json)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
          mbid=COALESCE(excluded.mbid, artists.mbid),
          url=COALESCE(excluded.url, artists.url),
          listeners=COALESCE(excluded.listeners, artists.listeners),
          global_playcount=COALESCE(excluded.global_playcount, artists.global_playcount),
          bio_summary=COALESCE(excluded.bio_summary, artists.bio_summary),
          raw_json=COALESCE(excluded.raw_json, artists.raw_json),
          updated_at=CURRENT_TIMESTAMP
        """,
        (
            name,
            normalized,
            fields.get("mbid"),
            fields.get("url"),
            fields.get("listeners"),
            fields.get("global_playcount"),
            fields.get("bio_summary"),
            dumps(fields["raw_json"]) if fields.get("raw_json") is not None else None,
        ),
    )
    row = conn.execute("SELECT id FROM artists WHERE name = ?", (name,)).fetchone()
    return int(row["id"])


def upsert_album(conn: sqlite3.Connection, artist_id: int, name: str | None) -> int | None:
    if not name:
        return None
    normalized = normalize_name(name)
    conn.execute(
        """
        INSERT INTO albums(artist_id, name, normalized_name)
        VALUES(?, ?, ?)
        ON CONFLICT(artist_id, normalized_name) DO UPDATE SET updated_at=CURRENT_TIMESTAMP
        """,
        (artist_id, name, normalized),
    )
    row = conn.execute(
        "SELECT id FROM albums WHERE artist_id = ? AND normalized_name = ?",
        (artist_id, normalized),
    ).fetchone()
    return int(row["id"])


def upsert_track(conn: sqlite3.Connection, artist_id: int, album_id: int | None, name: str, **fields: Any) -> int:
    normalized = normalize_name(name)
    conn.execute(
        """
        INSERT INTO tracks(artist_id, album_id, name, normalized_name, mbid, duration_ms, url, loved, raw_json)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(artist_id, normalized_name) DO UPDATE SET
          album_id=COALESCE(tracks.album_id, excluded.album_id),
          mbid=COALESCE(excluded.mbid, tracks.mbid),
          duration_ms=COALESCE(excluded.duration_ms, tracks.duration_ms),
          url=COALESCE(excluded.url, tracks.url),
          loved=COALESCE(excluded.loved, tracks.loved),
          raw_json=COALESCE(excluded.raw_json, tracks.raw_json),
          updated_at=CURRENT_TIMESTAMP
        """,
        (
            artist_id,
            album_id,
            name,
            normalized,
            fields.get("mbid"),
            fields.get("duration_ms"),
            fields.get("url"),
            fields.get("loved"),
            dumps(fields["raw_json"]) if fields.get("raw_json") is not None else None,
        ),
    )
    row = conn.execute(
        "SELECT id FROM tracks WHERE artist_id = ? AND normalized_name = ?",
        (artist_id, normalized),
    ).fetchone()
    return int(row["id"])


def upsert_tags(conn: sqlite3.Connection, names: Iterable[tuple[str, int | None]]) -> list[tuple[int, int | None]]:
    result: list[tuple[int, int | None]] = []
    for name, weight in names:
        normalized = normalize_name(name)
        if not normalized:
            continue
        conn.execute(
            """
            INSERT INTO tags(name, normalized_name) VALUES(?, ?)
            ON CONFLICT(normalized_name) DO NOTHING
            """,
            (name.strip(), normalized),
        )
        row = conn.execute("SELECT id FROM tags WHERE normalized_name = ?", (normalized,)).fetchone()
        result.append((int(row["id"]), weight))
    return result


def recompute_stats(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DELETE FROM user_artist_stats;
        INSERT INTO user_artist_stats(artist_id, playcount, first_played_at, last_played_at)
        SELECT t.artist_id, COUNT(*), MIN(s.played_at_utc), MAX(s.played_at_utc)
        FROM scrobbles s
        JOIN tracks t ON t.id = s.track_id
        GROUP BY t.artist_id;

        DELETE FROM user_track_stats;
        INSERT INTO user_track_stats(track_id, playcount, first_played_at, last_played_at)
        SELECT track_id, COUNT(*), MIN(played_at_utc), MAX(played_at_utc)
        FROM scrobbles
        GROUP BY track_id;

        DELETE FROM user_album_stats;
        INSERT INTO user_album_stats(album_id, playcount, first_played_at, last_played_at)
        SELECT t.album_id, COUNT(*), MIN(s.played_at_utc), MAX(s.played_at_utc)
        FROM scrobbles s
        JOIN tracks t ON t.id = s.track_id
        WHERE t.album_id IS NOT NULL
        GROUP BY t.album_id;

        UPDATE artists
        SET first_seen = (SELECT first_played_at FROM user_artist_stats WHERE artist_id = artists.id),
            last_seen = (SELECT last_played_at FROM user_artist_stats WHERE artist_id = artists.id);

        UPDATE tracks
        SET first_seen = (SELECT first_played_at FROM user_track_stats WHERE track_id = tracks.id),
            last_seen = (SELECT last_played_at FROM user_track_stats WHERE track_id = tracks.id);
        """
    )
    conn.commit()
