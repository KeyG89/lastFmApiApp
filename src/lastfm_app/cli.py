from __future__ import annotations

import argparse
from pathlib import Path

from .config import LastfmConfig, load_config
from .db import connect, init_db
from .importer import enrich_artists, enrich_tracks, import_full_history
from .lastfm import LastfmClient
from .reports import favorites, genres, status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lastfm-app", description="Import and analyze a Last.fm listening history.")
    parser.add_argument("--db", type=Path, help="Override SQLite database path.")
    sub = parser.add_subparsers(dest="command", required=True)

    init_parser = sub.add_parser("init-db", help="Create or migrate the local SQLite database.")
    init_parser.add_argument("--db", dest="command_db", type=Path, help="Override SQLite database path.")

    import_parser = sub.add_parser("import-history", help="Import full Last.fm scrobble history.")
    import_parser.add_argument("--db", dest="command_db", type=Path, help="Override SQLite database path.")
    import_parser.add_argument("--full", action="store_true", help="Confirm full history import.")
    import_parser.add_argument("--max-pages", type=int, help="Limit pages for smoke tests.")

    enrich = sub.add_parser("enrich", help="Fetch Last.fm artist/track metadata and tags.")
    enrich.add_argument("--db", dest="command_db", type=Path, help="Override SQLite database path.")
    enrich.add_argument("--artists", action="store_true", help="Enrich artists.")
    enrich.add_argument("--tracks", action="store_true", help="Enrich tracks.")
    enrich.add_argument("--limit", type=int, help="Limit number of artists/tracks enriched.")

    report = sub.add_parser("report", help="Print a local report.")
    report.add_argument("--db", dest="command_db", type=Path, help="Override SQLite database path.")
    report.add_argument("name", choices=["genres", "favorites"])
    report.add_argument("--limit", type=int, default=25)

    status_parser = sub.add_parser("status", help="Print database status.")
    status_parser.add_argument("--db", dest="command_db", type=Path, help="Override SQLite database path.")
    return parser


def client_from_config(db_override: Path | None = None, require_api: bool = True) -> tuple[LastfmConfig, object, object]:
    config = load_config(require_api=require_api)
    db_path = db_override or config.db_path
    conn = connect(db_path)
    init_db(conn)
    client = LastfmClient(config.api_key, config.app_name, config.request_delay)
    return config, conn, client


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    require_api = args.command in {"import-history", "enrich"}
    db_override = getattr(args, "command_db", None) or args.db
    config, conn, client = client_from_config(db_override=db_override, require_api=require_api)

    if args.command == "init-db":
        print(f"initialized database: {db_override or config.db_path}")
        return 0

    if args.command == "import-history":
        if not args.full and not args.max_pages:
            parser.error("import-history requires --full or --max-pages")
        pages, inserted = import_full_history(conn, client, config.username, max_pages=args.max_pages)
        print(f"import complete: pages={pages}, inserted={inserted}")
        return 0

    if args.command == "enrich":
        if not args.artists and not args.tracks:
            args.artists = True
            args.tracks = True
        done = 0
        if args.artists:
            done += enrich_artists(conn, client, config.username, limit=args.limit)
        if args.tracks:
            done += enrich_tracks(conn, client, config.username, limit=args.limit)
        print(f"enriched records: {done}")
        return 0

    if args.command == "report":
        print(genres(conn, args.limit) if args.name == "genres" else favorites(conn, args.limit))
        return 0

    if args.command == "status":
        print(status(conn))
        return 0

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
