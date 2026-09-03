# Music Data Operations

Use this reference after local setup is complete. Start with read-only or limited commands and make external changes only when the user clearly requests them.

## Contents

- Preflight
- Last.fm database import and enrichment
- Read-only database inspection
- Spotify account mirror
- Spotify playlist creation
- Protected Spotify mutations
- Shazam import and playlist generation
- Drum groove export
- Rate limits and recovery

## Preflight

```bash
.venv/bin/python Diagnostics/integration_doctor.py .
.venv/bin/lastfm-app status
.venv/bin/lastfm-app shazam status
```

Before any Spotify mutation, also run a controlled mirror sync and inspect protection state:

```bash
.venv/bin/lastfm-app spotify sync --limit 10 --delay 3
.venv/bin/lastfm-app spotify playlists --limit 50
```

## Last.fm database import and enrichment

Initialize or migrate the schema, then perform a one-page smoke import:

```bash
.venv/bin/lastfm-app init-db
.venv/bin/lastfm-app import-history --max-pages 1
.venv/bin/lastfm-app status
```

Only after the smoke import succeeds, import the complete history:

```bash
.venv/bin/lastfm-app import-history --full
```

Imports are resumable and deduplicate scrobbles by track and UTC timestamp. If a run stopped on a known Last.fm page, resume with:

```bash
.venv/bin/lastfm-app import-history --full --start-page <page-number>
```

Enrich in conservative batches first:

```bash
.venv/bin/lastfm-app enrich --artists --limit 100
.venv/bin/lastfm-app enrich --tracks --limit 250
.venv/bin/lastfm-app report favorites --limit 30
.venv/bin/lastfm-app report genres --limit 30
```

Run `enrich` without a limit only when the user requests full enrichment and accepts the API volume.

## Read-only database inspection

Prefer CLI reports. For questions not exposed by the CLI, use SQLite read-only mode and inspect `Docs/Architecture.md` plus the schema in `src/lastfm_app/db.py`, `spotify.py`, or `shazam.py` before writing a query.

```bash
sqlite3 -readonly data/lastfm.sqlite3 \
  "SELECT status, pages_fetched, rows_inserted, started_at, finished_at FROM import_runs ORDER BY id DESC LIMIT 5;"

sqlite3 -readonly data/lastfm.sqlite3 \
  "SELECT a.name, t.name, s.playcount FROM user_track_stats s JOIN tracks t ON t.id=s.track_id JOIN artists a ON a.id=t.artist_id ORDER BY s.playcount DESC LIMIT 25;"

sqlite3 -readonly data/lastfm.sqlite3 \
  "SELECT id, name, created_by_app, protected, total_tracks FROM spotify_playlists ORDER BY last_seen_at DESC LIMIT 50;"

sqlite3 -readonly data/lastfm.sqlite3 \
  "SELECT operation, target_name, status, protected_target, created_at FROM spotify_operation_backlog ORDER BY id DESC LIMIT 25;"

sqlite3 -readonly data/shazam.sqlite3 \
  "SELECT artist_name, track_name, genre FROM shazam_tracks WHERE spotify_track_id IS NULL ORDER BY shazamed_at DESC LIMIT 50;"
```

Do not make manual SQL writes as part of normal operation. Before an explicitly requested repair, create a consistent SQLite backup:

```bash
sqlite3 data/lastfm.sqlite3 ".backup '<backup-path>/lastfm.sqlite3'"
sqlite3 data/shazam.sqlite3 ".backup '<backup-path>/shazam.sqlite3'"
```

## Spotify account mirror

Authenticate once, then sync in batches:

```bash
.venv/bin/lastfm-app spotify auth
.venv/bin/lastfm-app spotify sync --limit 10 --delay 3
.venv/bin/lastfm-app spotify playlists --limit 50
```

To continue gradually, increase the limit. To diagnose one known playlist, repeat `--playlist-id` as needed:

```bash
.venv/bin/lastfm-app spotify sync --playlist-id <spotify-playlist-id> --delay 3
```

The mirror lives in `data/lastfm.sqlite3`. Non-owned playlists may be listed but their item fetch is skipped when Spotify would deny access.

## Spotify playlist creation

List built-in inputs:

```bash
.venv/bin/lastfm-app spotify presets --verbose
```

Always match first. A dry run queries Spotify and records local match/backlog data, but does not create a remote playlist:

```bash
.venv/bin/lastfm-app spotify create --preset morning-rock-bangers --dry-run
```

After reviewing matches and receiving authorization to create it, omit `--dry-run`. Playlists are private by default:

```bash
.venv/bin/lastfm-app spotify create --preset morning-rock-bangers
```

For a custom playlist, use a UTF-8 text file with one `Artist - Track` entry per line:

```text
Massive Attack - Teardrop
Portishead - Roads
```

```bash
.venv/bin/lastfm-app spotify create --input <playlist.txt> --name "Playlist name" --dry-run
.venv/bin/lastfm-app spotify create --input <playlist.txt> --name "Playlist name"
```

Use `--public` only when the user explicitly requests public visibility.

## Protected Spotify mutations

The safety cutoff is `2026-05-31`. Playlists created by this app on or after the cutoff can be edited normally. Synced playlists with unknown creation dates, external playlists, and older playlists are protected.

1. Sync and list playlists.
2. Identify the exact ID and protection state.
3. If protected, run the requested command without `--confirm`; the CLI blocks it and prints the required exact phrase.
4. Show the target and effect to the user. Proceed only after explicit approval.
5. Re-run with the exact phrase unchanged.

```bash
.venv/bin/lastfm-app spotify rename <playlist-id> "New name"
.venv/bin/lastfm-app spotify unfollow <playlist-id>
```

Do not invent the confirmation phrase or edit SQLite protection flags. Spotify Web API has no delete endpoint; `unfollow` removes the playlist from the account.

## Shazam import and playlist generation

Import the Shazam web CSV into its separate database, then link it to local Last.fm data:

```bash
.venv/bin/lastfm-app shazam init
.venv/bin/lastfm-app shazam import <path-to-shazam.csv> --link-lastfm
.venv/bin/lastfm-app shazam enrich-lastfm
.venv/bin/lastfm-app shazam status
```

Spotify matching performs remote searches and writes matches locally, but does not create playlists:

```bash
.venv/bin/lastfm-app shazam match-spotify --limit 25
```

Generate and inspect local plans before export:

```bash
.venv/bin/lastfm-app shazam playlists --show --limit 50
```

`shazam export-spotify` has no dry-run mode and creates remote playlists. Run it only after explicit authorization. Prefer existing matches and a delay:

```bash
.venv/bin/lastfm-app shazam export-spotify --no-match --delay 10 --show
.venv/bin/lastfm-app shazam spotify-exports --limit 20
```

## Drum groove export

Use the verified markdown draft, dry-run one playlist first, and keep duplicate prevention enabled:

```bash
.venv/bin/lastfm-app spotify drum-grooves --dry-run --limit 1 --delay 0
.venv/bin/lastfm-app spotify drum-grooves --dry-run --delay 0
```

Only after review and explicit authorization:

```bash
.venv/bin/lastfm-app spotify drum-grooves --delay 10
```

Do not use `--no-skip-existing` unless duplicate playlist creation is explicitly requested.

## Rate limits and recovery

- The Spotify client retries short limits and stops when `Retry-After` exceeds `SPOTIFY_MAX_RATE_LIMIT_SLEEP_SECONDS`.
- Report the retry duration and stop. Resume later with a limited command or explicit playlist ID.
- Do not delete the token cache as a rate-limit workaround.
- If authorization scopes changed, re-run `spotify auth`; if the API is rate limited, reauthorization usually does not remove the limit.
- Last.fm imports record each run in `import_runs`; inspect the latest run before choosing `--start-page`.
