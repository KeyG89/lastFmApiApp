from __future__ import annotations

import sqlite3


def favorites(conn: sqlite3.Connection, limit: int = 25) -> str:
    rows = conn.execute(
        """
        SELECT ar.name AS artist, tr.name AS track, uts.playcount, uts.first_played_at, uts.last_played_at
        FROM user_track_stats uts
        JOIN tracks tr ON tr.id = uts.track_id
        JOIN artists ar ON ar.id = tr.artist_id
        ORDER BY uts.playcount DESC, uts.last_played_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    lines = ["# Favorite Tracks", ""]
    for idx, row in enumerate(rows, start=1):
        lines.append(f"{idx}. {row['artist']} - {row['track']} ({row['playcount']} plays)")
    return "\n".join(lines)


def genres(conn: sqlite3.Connection, limit: int = 30) -> str:
    rows = conn.execute(
        """
        SELECT tg.name, COUNT(DISTINCT at.artist_id) AS artists, SUM(uas.playcount) AS weighted_plays
        FROM artist_tags at
        JOIN tags tg ON tg.id = at.tag_id
        JOIN user_artist_stats uas ON uas.artist_id = at.artist_id
        GROUP BY tg.id
        ORDER BY weighted_plays DESC, artists DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    lines = ["# Genre / Tag Profile", ""]
    for idx, row in enumerate(rows, start=1):
        lines.append(f"{idx}. {row['name']} - {row['weighted_plays'] or 0} weighted plays across {row['artists']} artists")
    return "\n".join(lines)


def status(conn: sqlite3.Connection) -> str:
    counts = {}
    for table in ("artists", "albums", "tracks", "scrobbles", "tags", "api_cache"):
        counts[table] = conn.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()["count"]
    last_run = conn.execute(
        "SELECT command, status, started_at, finished_at, pages_fetched, rows_inserted, error FROM import_runs ORDER BY id DESC LIMIT 1"
    ).fetchone()
    lines = ["# Last.fm App Status", ""]
    for table, count in counts.items():
        lines.append(f"- {table}: {count}")
    if last_run:
        lines.extend(
            [
                "",
                f"last run: {last_run['command']} / {last_run['status']}",
                f"pages: {last_run['pages_fetched']}, inserted: {last_run['rows_inserted']}",
            ]
        )
        if last_run["error"]:
            lines.append(f"error: {last_run['error']}")
    return "\n".join(lines)
