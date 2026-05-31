#!/usr/bin/env python3
from __future__ import annotations

import sqlite3
import sys

from lastfm_app.shazam import connect_shazam, ensure_shazam_schema, load_shazam_config


def main() -> int:
    try:
        config = load_shazam_config()
        conn = connect_shazam(config.db_path)
        ensure_shazam_schema(conn)
        conn.execute("SELECT 1").fetchone()
        tracks = conn.execute("SELECT COUNT(*) AS count FROM shazam_tracks").fetchone()["count"]
    except (OSError, sqlite3.Error, ValueError) as error:
        print(f"fail: {error}")
        return 1

    print("Shazam diagnostics")
    print(f"database: {config.db_path}")
    print(f"tracks: {tracks}")
    print("sqlite: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
