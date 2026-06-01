from __future__ import annotations

import argparse
from pathlib import Path

from .config import LastfmConfig, load_config
from .db import connect, init_db
from .drum_grooves import export_verified_drum_grooves_to_spotify, parse_verified_drum_grooves
from .importer import enrich_artists, enrich_tracks, import_full_history
from .lastfm import LastfmClient
from .playlist_presets import PRESETS, PlaylistPreset, PlaylistTrack, parse_track_lines
from .reports import favorites, genres, status
from .shazam import (
    connect_shazam,
    enrich_from_lastfm,
    ensure_shazam_schema,
    export_shazam_playlists_to_spotify,
    generate_shazam_playlists,
    import_shazam_file,
    link_lastfm_tracks,
    load_shazam_config,
    match_spotify_tracks,
    playlist_report,
    shazam_status,
    spotify_export_report,
)
from .spotify import (
    SpotifyError,
    SpotifyRateLimitError,
    SpotifyClient,
    authenticate,
    ensure_spotify_schema,
    load_spotify_config,
    log_operation,
    protected_confirmation_phrase,
    require_playlist_confirmation,
    save_spotify_matches,
    sync_spotify_playlists,
    upsert_spotify_playlist,
)


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
    import_parser.add_argument("--start-page", type=int, default=1, help="Resume import from a specific Last.fm page.")

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

    spotify = sub.add_parser("spotify", help="Authenticate with Spotify and create playlists.")
    spotify_sub = spotify.add_subparsers(dest="spotify_command", required=True)
    spotify_auth = spotify_sub.add_parser("auth", help="Authorize Spotify playlist access with PKCE.")
    spotify_auth.add_argument("--no-browser", action="store_true", help="Print the auth URL without opening a browser.")

    spotify_presets = spotify_sub.add_parser("presets", help="List built-in playlist presets.")
    spotify_presets.add_argument("--verbose", action="store_true", help="Print tracks in each preset.")

    spotify_sync = spotify_sub.add_parser("sync", help="Mirror Spotify account playlists and tracks into SQLite.")
    spotify_sync.add_argument("--db", dest="command_db", type=Path, help="Override SQLite database path.")
    spotify_sync.add_argument("--playlist-id", action="append", help="Sync only this playlist id. Can be repeated.")
    spotify_sync.add_argument("--limit", type=int, help="Limit number of playlists processed.")
    spotify_sync.add_argument("--delay", type=float, default=1.0, help="Delay in seconds before fetching each owned playlist's items.")

    spotify_playlists = spotify_sub.add_parser("playlists", help="List synced Spotify playlists and protection status.")
    spotify_playlists.add_argument("--db", dest="command_db", type=Path, help="Override SQLite database path.")
    spotify_playlists.add_argument("--limit", type=int, default=50)

    spotify_create = spotify_sub.add_parser("create", help="Create a Spotify playlist from a preset or text file.")
    spotify_create.add_argument("--db", dest="command_db", type=Path, help="Override SQLite database path.")
    spotify_create.add_argument("--preset", choices=sorted(PRESETS), help="Built-in playlist preset.")
    spotify_create.add_argument("--input", type=Path, help="Text file with one 'Artist - Track' per line.")
    spotify_create.add_argument("--name", help="Playlist name override.")
    spotify_create.add_argument("--description", default="", help="Playlist description override.")
    spotify_create.add_argument("--public", action="store_true", help="Create a public playlist instead of private.")
    spotify_create.add_argument("--dry-run", action="store_true", help="Match tracks but do not create a playlist.")

    spotify_drum = spotify_sub.add_parser("drum-grooves", help="Create Spotify playlists from the verified drum groove markdown.")
    spotify_drum.add_argument("--db", dest="command_db", type=Path, help="Override SQLite database path.")
    spotify_drum.add_argument("--input", type=Path, default=Path("Docs/DrumGrooveStudyPlaylistsVerified.md"))
    spotify_drum.add_argument("--public", action="store_true", help="Create public Spotify playlists instead of private.")
    spotify_drum.add_argument("--delay", type=float, default=10.0, help="Delay in seconds before each Spotify API request.")
    spotify_drum.add_argument("--limit", type=int, help="Limit number of playlists processed.")
    spotify_drum.add_argument("--no-skip-existing", action="store_true", help="Create playlists even when a playlist with the same name is found.")
    spotify_drum.add_argument("--dry-run", action="store_true", help="Match tracks and report what would be created without creating playlists.")

    spotify_rename = spotify_sub.add_parser("rename", help="Rename a Spotify playlist.")
    spotify_rename.add_argument("--db", dest="command_db", type=Path, help="Override SQLite database path.")
    spotify_rename.add_argument("playlist_id")
    spotify_rename.add_argument("name")
    spotify_rename.add_argument("--confirm", help="Required exact confirmation phrase for protected playlists.")

    spotify_unfollow = spotify_sub.add_parser("unfollow", help="Remove a playlist from the Spotify account.")
    spotify_unfollow.add_argument("--db", dest="command_db", type=Path, help="Override SQLite database path.")
    spotify_unfollow.add_argument("playlist_id")
    spotify_unfollow.add_argument("--confirm", help="Required exact confirmation phrase for protected playlists.")

    shazam = sub.add_parser("shazam", help="Import and organize Shazam discoveries.")
    shazam.add_argument("--shazam-db", type=Path, help="Override Shazam SQLite database path.")
    shazam_sub = shazam.add_subparsers(dest="shazam_command", required=True)

    shazam_init = shazam_sub.add_parser("init", help="Create or migrate the local Shazam database.")
    shazam_init.set_defaults(_shazam_parser=True)

    shazam_import = shazam_sub.add_parser("import", help="Import the CSV downloaded from Shazam on the web into the local Shazam database.")
    shazam_import.add_argument("path", type=Path)
    shazam_import.add_argument("--link-lastfm", action="store_true", help="Link and enrich imported tracks from the Last.fm database after import.")

    shazam_link = shazam_sub.add_parser("link-lastfm", help="Link Shazam tracks to matching Last.fm tracks.")
    shazam_link.set_defaults(_shazam_parser=True)

    shazam_enrich = shazam_sub.add_parser("enrich-lastfm", help="Enrich linked Shazam tracks with local Last.fm tags.")
    shazam_enrich.set_defaults(_shazam_parser=True)

    shazam_match = shazam_sub.add_parser("match-spotify", help="Match Shazam tracks to Spotify via the Spotify API.")
    shazam_match.add_argument("--limit", type=int, help="Limit number of unmatched Shazam tracks checked.")

    shazam_playlists = shazam_sub.add_parser("playlists", help="Generate Shazam calm-to-energetic and genre playlists.")
    shazam_playlists.add_argument("--show", action="store_true", help="Print generated playlist contents.")
    shazam_playlists.add_argument("--limit", type=int, help="Limit printed tracks per playlist when using --show.")

    shazam_export = shazam_sub.add_parser("export-spotify", help="Create Spotify playlists from generated Shazam playlists.")
    shazam_export.add_argument("--public", action="store_true", help="Create public Spotify playlists instead of private.")
    shazam_export.add_argument("--no-match", action="store_true", help="Use existing Spotify matches only; do not search Spotify for missing tracks.")
    shazam_export.add_argument("--delay", type=float, default=0.0, help="Delay in seconds before each Spotify create/add request.")
    shazam_export.add_argument("--show", action="store_true", help="Print recent export records after export.")

    shazam_exports = shazam_sub.add_parser("spotify-exports", help="Show recorded Shazam Spotify playlist exports.")
    shazam_exports.add_argument("--limit", type=int, default=20)

    shazam_status_parser = shazam_sub.add_parser("status", help="Print Shazam database status.")
    shazam_status_parser.set_defaults(_shazam_parser=True)
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
        pages, inserted = import_full_history(
            conn,
            client,
            config.username,
            max_pages=args.max_pages,
            start_page=args.start_page,
        )
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

    if args.command == "spotify":
        if args.spotify_command == "auth":
            try:
                spotify_config = load_spotify_config(require_client=True)
            except ValueError as error:
                parser.error(str(error))
            token = authenticate(spotify_config, open_browser=not args.no_browser)
            print(f"spotify auth ok: scopes={token.get('scope', '')}")
            return 0

        if args.spotify_command == "presets":
            for key, preset in PRESETS.items():
                print(f"{key}: {preset.name} ({len(preset.tracks)} tracks)")
                if args.verbose:
                    for track in preset.tracks:
                        print(f"  - {track.artist} - {track.track}")
            return 0

        if args.spotify_command == "sync":
            spotify_client = _spotify_client_or_error(parser)
            try:
                result = sync_spotify_playlists(
                    conn,
                    spotify_client,
                    playlist_ids=set(args.playlist_id or []) or None,
                    limit=args.limit,
                    delay_seconds=args.delay,
                )
            except SpotifyRateLimitError as error:
                log_operation(
                    conn,
                    "sync_library",
                    "spotify_account",
                    "rate_limited",
                    details={"retry_after_seconds": error.retry_after_seconds, "error": str(error)},
                )
                raise SystemExit(f"spotify sync rate limited: {error}")
            except SpotifyError as error:
                log_operation(
                    conn,
                    "sync_library",
                    "spotify_account",
                    "failed",
                    details={"error": str(error)},
                )
                raise SystemExit(f"spotify sync failed: {error}\nRun spotify auth again if this says insufficient scope.")
            print(f"spotify sync complete: playlists={result['playlists']}, playlist_tracks={result['playlist_tracks']}")
            return 0

        if args.spotify_command == "playlists":
            ensure_spotify_schema(conn)
            rows = conn.execute(
                """
                SELECT id, name, total_tracks, protected, created_by_app, created_at, external_url
                FROM spotify_playlists
                ORDER BY last_seen_at DESC, name COLLATE NOCASE
                LIMIT ?
                """,
                (args.limit,),
            ).fetchall()
            if not rows:
                print("No synced Spotify playlists. Run: lastfm-app spotify sync")
                return 0
            for row in rows:
                state = "protected" if int(row["protected"]) else "editable"
                source = "app" if int(row["created_by_app"]) else "synced"
                created = row["created_at"] or "unknown"
                print(f"{row['id']} | {state} | {source} | tracks={row['total_tracks']} | created={created} | {row['name']}")
            return 0

        if args.spotify_command == "create":
            tracks, default_name, default_description = _spotify_playlist_input(args)
            if not tracks:
                parser.error("spotify create needs --preset or --input")
            spotify_client = _spotify_client_or_error(parser)
            matches: list[tuple[PlaylistTrack, dict | None]] = []
            for wanted in tracks:
                match = spotify_client.search_track(wanted)
                matches.append((wanted, match))
                if match:
                    artists = ", ".join(artist.get("name", "") for artist in match.get("artists", []))
                    print(f"matched: {wanted.artist} - {wanted.track} -> {artists} - {match.get('name')} [{match.get('uri')}]")
                else:
                    print(f"missing: {wanted.artist} - {wanted.track}")
            save_spotify_matches(conn, matches)
            uris = [match["uri"] for _, match in matches if match and match.get("uri")]
            if args.dry_run:
                log_operation(
                    conn,
                    "match_playlist_dry_run",
                    "playlist",
                    "done",
                    target_name=args.name or default_name,
                    details={"matched": len(uris), "total": len(tracks), "preset": args.preset},
                )
                print(f"dry run: matched {len(uris)}/{len(tracks)} tracks")
                return 0
            if not uris:
                raise SystemExit("No Spotify tracks matched; playlist was not created.")
            name = args.name or default_name
            description = args.description or default_description
            playlist = spotify_client.create_playlist(name, description, public=args.public)
            spotify_client.add_items(playlist["id"], uris)
            upsert_spotify_playlist(conn, spotify_client.me().get("id"), playlist, created_by_app=True)
            log_operation(
                conn,
                "create_playlist",
                "playlist",
                "done",
                target_id=playlist["id"],
                target_name=name,
                protected_target=False,
                details={"track_count": len(uris), "preset": args.preset, "input": str(args.input) if args.input else None},
            )
            print(f"spotify playlist created: {playlist.get('external_urls', {}).get('spotify', playlist.get('id'))}")
            print(f"added {len(uris)}/{len(tracks)} tracks")
            return 0

        if args.spotify_command == "drum-grooves":
            if not args.input.exists():
                parser.error(f"drum groove input file does not exist: {args.input}")
            parsed = parse_verified_drum_grooves(args.input)
            print(f"drum groove playlists parsed: {len(parsed)}")
            spotify_client = _spotify_client_or_error(parser)
            try:
                result = export_verified_drum_grooves_to_spotify(
                    conn,
                    spotify_client,
                    args.input,
                    public=args.public,
                    delay_seconds=args.delay,
                    limit=args.limit,
                    skip_existing=not args.no_skip_existing,
                    dry_run=args.dry_run,
                )
            except SpotifyRateLimitError as error:
                log_operation(
                    conn,
                    "create_drum_groove_playlist",
                    "playlist",
                    "rate_limited",
                    details={"retry_after_seconds": error.retry_after_seconds, "error": str(error)},
                )
                raise SystemExit(f"drum groove Spotify export rate limited: {error}")
            print(
                "drum groove spotify export complete: "
                f"playlists={result['playlists']}, created={result['created']}, skipped={result['skipped']}, "
                f"tracks_matched={result['tracks_matched']}, tracks_missing={result['tracks_missing']}"
            )
            for playlist in result["created_playlists"]:
                print(
                    "created: "
                    f"{playlist['name']} | added={playlist['tracks_added']} | "
                    f"missing={playlist['tracks_missing']} | {playlist.get('url') or playlist['id']}"
                )
            for playlist in result["skipped_playlists"][:20]:
                print(f"skipped: {playlist['name']} | {playlist['reason']}")
            return 0

        if args.spotify_command == "rename":
            ensure_spotify_schema(conn)
            require_playlist_confirmation(conn, "rename", args.playlist_id, args.confirm)
            spotify_client = _spotify_client_or_error(parser)
            spotify_client.update_playlist_details(args.playlist_id, name=args.name)
            log_operation(
                conn,
                "rename",
                "playlist",
                "done",
                target_id=args.playlist_id,
                target_name=args.name,
                protected_target=False,
                confirmation=args.confirm,
            )
            print(f"renamed playlist {args.playlist_id} -> {args.name}")
            return 0

        if args.spotify_command == "unfollow":
            ensure_spotify_schema(conn)
            require_playlist_confirmation(conn, "unfollow", args.playlist_id, args.confirm)
            spotify_client = _spotify_client_or_error(parser)
            spotify_client.unfollow_playlist(args.playlist_id)
            log_operation(
                conn,
                "unfollow",
                "playlist",
                "done",
                target_id=args.playlist_id,
                protected_target=False,
                confirmation=args.confirm,
            )
            print(f"unfollowed playlist {args.playlist_id}")
            return 0

    if args.command == "shazam":
        shazam_db = args.shazam_db or load_shazam_config().db_path
        shazam_conn = connect_shazam(shazam_db)

        if args.shazam_command == "init":
            ensure_shazam_schema(shazam_conn)
            print(f"initialized Shazam database: {shazam_db}")
            return 0

        if args.shazam_command == "import":
            result = import_shazam_file(shazam_conn, args.path)
            linked = 0
            enriched = 0
            if args.link_lastfm:
                linked = link_lastfm_tracks(shazam_conn, conn)
                enriched = enrich_from_lastfm(shazam_conn, conn)
            print(
                "shazam import complete: "
                f"seen={result['rows_seen']}, inserted={result['rows_inserted']}, "
                f"updated={result['rows_updated']}, lastfm_linked={linked}, lastfm_enriched={enriched}"
            )
            return 0

        if args.shazam_command == "link-lastfm":
            linked = link_lastfm_tracks(shazam_conn, conn)
            print(f"shazam lastfm links added: {linked}")
            return 0

        if args.shazam_command == "enrich-lastfm":
            enriched = enrich_from_lastfm(shazam_conn, conn)
            print(f"shazam tracks enriched from lastfm tags: {enriched}")
            return 0

        if args.shazam_command == "match-spotify":
            spotify_client = _spotify_client_or_error(parser)
            try:
                result = match_spotify_tracks(shazam_conn, spotify_client, limit=args.limit)
            except SpotifyRateLimitError as error:
                raise SystemExit(f"shazam spotify matching rate limited: {error}")
            print(f"shazam spotify matching complete: checked={result['checked']}, matched={result['matched']}")
            return 0

        if args.shazam_command == "playlists":
            result = generate_shazam_playlists(shazam_conn)
            print(f"shazam playlists generated: playlists={result['playlists']}, items={result['items']}")
            if args.show:
                print()
                print(playlist_report(shazam_conn, limit=args.limit))
            return 0

        if args.shazam_command == "export-spotify":
            spotify_client = _spotify_client_or_error(parser)
            try:
                result = export_shazam_playlists_to_spotify(
                    shazam_conn,
                    spotify_client,
                    public=args.public,
                    match_missing=not args.no_match,
                    request_delay_seconds=args.delay,
                )
            except SpotifyRateLimitError as error:
                raise SystemExit(f"shazam spotify export rate limited: {error}")
            print(
                "shazam spotify export complete: "
                f"playlists={result['playlists']}, exported={result['exported']}, "
                f"tracks_added={result['tracks_added']}, tracks_missing={result['tracks_missing']}"
            )
            if args.show:
                print()
                print(spotify_export_report(shazam_conn))
            return 0

        if args.shazam_command == "spotify-exports":
            print(spotify_export_report(shazam_conn, limit=args.limit))
            return 0

        if args.shazam_command == "status":
            print(shazam_status(shazam_conn))
            return 0

    parser.error("unknown command")
    return 2


def _spotify_playlist_input(args: argparse.Namespace) -> tuple[list[PlaylistTrack], str, str]:
    if args.preset:
        preset: PlaylistPreset = PRESETS[args.preset]
        return list(preset.tracks), preset.name, preset.description
    if args.input:
        return parse_track_lines(args.input.read_text(encoding="utf-8")), args.name or args.input.stem, args.description
    return [], args.name or "Last.fm Playlist", args.description


def _spotify_client_or_error(parser: argparse.ArgumentParser) -> SpotifyClient:
    try:
        spotify_config = load_spotify_config(require_client=True)
        return SpotifyClient(spotify_config)
    except ValueError as error:
        parser.error(str(error))
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
