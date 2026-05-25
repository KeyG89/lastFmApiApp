from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any

from . import db
from .lastfm import LastfmClient, params_hash


def text_value(value: Any) -> str | None:
    if isinstance(value, dict):
        nested = value.get("#text")
        return str(nested).strip() if nested else None
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def int_value(value: Any) -> int | None:
    text = text_value(value)
    if text is None:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def parse_scrobble_time(track: dict[str, Any]) -> str | None:
    if "@attr" in track and track["@attr"].get("nowplaying") == "true":
        return None
    timestamp = text_value(track.get("date", {}).get("uts") if isinstance(track.get("date"), dict) else None)
    if not timestamp:
        return None
    played_at = datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
    return played_at.isoformat().replace("+00:00", "Z")


def get_cached_or_call(
    conn: sqlite3.Connection,
    client: LastfmClient,
    method: str,
    params: dict[str, Any],
    use_cache: bool = True,
) -> dict[str, Any]:
    clean_params = {key: value for key, value in params.items() if value is not None}
    digest = params_hash(clean_params)
    if use_cache:
        row = conn.execute(
            "SELECT response_json FROM api_cache WHERE method = ? AND params_hash = ?",
            (method, digest),
        ).fetchone()
        if row:
            import json

            return json.loads(row["response_json"])
    payload = client.call(method, **clean_params)
    conn.execute(
        """
        INSERT OR REPLACE INTO api_cache(method, params_hash, params_json, response_json, status)
        VALUES(?, ?, ?, ?, 'ok')
        """,
        (method, digest, db.dumps(clean_params), db.dumps(payload)),
    )
    conn.commit()
    return payload


def iter_recent_tracks(
    conn: sqlite3.Connection,
    client: LastfmClient,
    username: str,
    limit: int = 200,
    max_pages: int | None = None,
) -> Iterator[tuple[int, int, list[dict[str, Any]]]]:
    page = 1
    total_pages = 1
    while page <= total_pages:
        payload = get_cached_or_call(
            conn,
            client,
            "user.getRecentTracks",
            {"user": username, "limit": limit, "page": page},
            use_cache=False,
        )
        recent = payload.get("recenttracks", {})
        attr = recent.get("@attr", {})
        total_pages = int(attr.get("totalPages") or 1)
        tracks = recent.get("track") or []
        if isinstance(tracks, dict):
            tracks = [tracks]
        yield page, total_pages, tracks
        page += 1
        if max_pages is not None and page > max_pages:
            break


def import_track_scrobble(conn: sqlite3.Connection, track: dict[str, Any]) -> bool:
    played_at = parse_scrobble_time(track)
    if played_at is None:
        return False
    artist_name = text_value(track.get("artist")) or "Unknown Artist"
    track_name = text_value(track.get("name")) or "Unknown Track"
    album_name = text_value(track.get("album"))
    artist_id = db.upsert_artist(conn, artist_name, mbid=text_value(track.get("artist", {}).get("mbid")) if isinstance(track.get("artist"), dict) else None)
    album_id = db.upsert_album(conn, artist_id, album_name)
    track_id = db.upsert_track(
        conn,
        artist_id,
        album_id,
        track_name,
        mbid=text_value(track.get("mbid")),
        url=text_value(track.get("url")),
        loved=int_value(track.get("loved")),
    )
    before = conn.total_changes
    conn.execute(
        """
        INSERT OR IGNORE INTO scrobbles(track_id, played_at_utc, raw_artist_name, raw_track_name, raw_album_name, raw_json)
        VALUES(?, ?, ?, ?, ?, ?)
        """,
        (track_id, played_at, artist_name, track_name, album_name, db.dumps(track)),
    )
    return conn.total_changes > before


def import_full_history(
    conn: sqlite3.Connection,
    client: LastfmClient,
    username: str,
    max_pages: int | None = None,
) -> tuple[int, int]:
    run = conn.execute(
        "INSERT INTO import_runs(command, status) VALUES('import-history', 'running')"
    )
    run_id = int(run.lastrowid)
    pages = 0
    inserted = 0
    try:
        for page, total_pages, tracks in iter_recent_tracks(conn, client, username, max_pages=max_pages):
            for track in tracks:
                if import_track_scrobble(conn, track):
                    inserted += 1
            pages += 1
            conn.execute(
                "UPDATE import_runs SET pages_fetched = ?, rows_inserted = ? WHERE id = ?",
                (pages, inserted, run_id),
            )
            conn.commit()
            print(f"page {page}/{total_pages}: inserted={inserted}")
        db.recompute_stats(conn)
        conn.execute(
            "UPDATE import_runs SET status = 'done', finished_at = CURRENT_TIMESTAMP, pages_fetched = ?, rows_inserted = ? WHERE id = ?",
            (pages, inserted, run_id),
        )
        conn.commit()
        return pages, inserted
    except Exception as error:
        conn.execute(
            "UPDATE import_runs SET status = 'failed', finished_at = CURRENT_TIMESTAMP, error = ? WHERE id = ?",
            (str(error), run_id),
        )
        conn.commit()
        raise


def tag_pairs(payload: dict[str, Any]) -> list[tuple[str, int | None]]:
    tags = payload.get("toptags", {}).get("tag") or []
    if isinstance(tags, dict):
        tags = [tags]
    return [(text_value(tag.get("name")) or "", int_value(tag.get("count"))) for tag in tags if isinstance(tag, dict)]


def enrich_artists(conn: sqlite3.Connection, client: LastfmClient, username: str, limit: int | None = None) -> int:
    rows = conn.execute(
        """
        SELECT a.id, a.name
        FROM artists a
        LEFT JOIN artist_tags at ON at.artist_id = a.id
        GROUP BY a.id
        ORDER BY COALESCE((SELECT playcount FROM user_artist_stats WHERE artist_id = a.id), 0) DESC
        LIMIT COALESCE(?, -1)
        """,
        (limit,),
    ).fetchall()
    count = 0
    for row in rows:
        info = get_cached_or_call(conn, client, "artist.getInfo", {"artist": row["name"], "username": username})
        artist = info.get("artist", {})
        stats = artist.get("stats", {}) if isinstance(artist, dict) else {}
        conn.execute(
            """
            UPDATE artists
            SET mbid = COALESCE(?, mbid),
                url = COALESCE(?, url),
                listeners = COALESCE(?, listeners),
                global_playcount = COALESCE(?, global_playcount),
                bio_summary = COALESCE(?, bio_summary),
                raw_json = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                text_value(artist.get("mbid")),
                text_value(artist.get("url")),
                int_value(stats.get("listeners")),
                int_value(stats.get("playcount")),
                text_value(artist.get("bio", {}).get("summary") if isinstance(artist.get("bio"), dict) else None),
                db.dumps(artist),
                row["id"],
            ),
        )
        tags_payload = get_cached_or_call(conn, client, "artist.getTopTags", {"artist": row["name"]})
        for tag_id, weight in db.upsert_tags(conn, tag_pairs(tags_payload)):
            conn.execute(
                "INSERT OR REPLACE INTO artist_tags(artist_id, tag_id, weight, source) VALUES(?, ?, ?, 'lastfm')",
                (row["id"], tag_id, weight),
            )
        conn.commit()
        count += 1
    return count


def enrich_tracks(conn: sqlite3.Connection, client: LastfmClient, username: str, limit: int | None = None) -> int:
    rows = conn.execute(
        """
        SELECT t.id, t.name, a.name AS artist_name
        FROM tracks t
        JOIN artists a ON a.id = t.artist_id
        ORDER BY COALESCE((SELECT playcount FROM user_track_stats WHERE track_id = t.id), 0) DESC
        LIMIT COALESCE(?, -1)
        """,
        (limit,),
    ).fetchall()
    count = 0
    for row in rows:
        info = get_cached_or_call(
            conn,
            client,
            "track.getInfo",
            {"artist": row["artist_name"], "track": row["name"], "username": username},
        )
        track = info.get("track", {})
        conn.execute(
            """
            UPDATE tracks
            SET mbid = COALESCE(?, mbid),
                duration_ms = COALESCE(?, duration_ms),
                url = COALESCE(?, url),
                loved = COALESCE(?, loved),
                raw_json = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                text_value(track.get("mbid")),
                int_value(track.get("duration")),
                text_value(track.get("url")),
                int_value(track.get("userloved")),
                db.dumps(track),
                row["id"],
            ),
        )
        tags_payload = get_cached_or_call(
            conn,
            client,
            "track.getTopTags",
            {"artist": row["artist_name"], "track": row["name"]},
        )
        for tag_id, weight in db.upsert_tags(conn, tag_pairs(tags_payload)):
            conn.execute(
                "INSERT OR REPLACE INTO track_tags(track_id, tag_id, weight, source) VALUES(?, ?, ?, 'lastfm')",
                (row["id"], tag_id, weight),
            )
        conn.commit()
        count += 1
    return count
