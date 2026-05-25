#!/usr/bin/env python3
from __future__ import annotations

import os
import sqlite3
import sys

from lastfm_app.config import load_config
from lastfm_app.db import connect, init_db


def present(name: str) -> str:
    return "present" if os.environ.get(name) else "missing"


def main() -> int:
    try:
        config = load_config(require_api=False)
        conn = connect(config.db_path)
        init_db(conn)
        conn.execute("SELECT 1").fetchone()
    except (OSError, sqlite3.Error, ValueError) as error:
        print(f"fail: {error}")
        return 1

    print("Last.fm diagnostics")
    print(f"database: {config.db_path}")
    print(f"LASTFM_API_KEY: {present('LASTFM_API_KEY')}")
    print(f"LASTFM_USERNAME: {present('LASTFM_USERNAME')}")
    print(f"LASTFM_SHARED_SECRET: {present('LASTFM_SHARED_SECRET')}")
    print("sqlite: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
