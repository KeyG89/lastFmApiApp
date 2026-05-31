# Architecture

Project kind: `python`.

The app is a local data pipeline with a thin CLI:

- `src/lastfm_app/cli.py`: command surface for import, enrichment, status, and reports.
- `src/lastfm_app/lastfm.py`: official Last.fm API client with retry/backoff.
- `src/lastfm_app/importer.py`: pagination, scrobble parsing, metadata enrichment, and API cache usage.
- `src/lastfm_app/db.py`: SQLite connection, schema, upserts, tag normalization, and aggregate stats.
- `src/lastfm_app/reports.py`: local summaries used as the first playlist intelligence layer.
- `src/lastfm_app/spotify.py`: Spotify PKCE auth, playlist creation, account mirror tables, safety confirmations, and rate-limit handling.
- `src/lastfm_app/shazam.py`: dedicated Shazam SQLite database, CSV/JSON import, Last.fm/Spotify linking, and generated playlist plans.

Generated databases live under `data/` by default and are ignored by git. Secrets live in `.env`, never in tracked files.

## Databases

- `data/lastfm.sqlite3`: canonical Last.fm music memory, Last.fm metadata, local Spotify mirror tables, Spotify operation backlog, and Spotify-to-Last.fm links.
- `data/shazam.sqlite3`: imported Shazam discoveries, raw source rows, optional Last.fm/Spotify links, and generated Shazam playlist plans.

Shazam stays in a separate database because it is a discovery inbox rather than a listening-history source. Cross-database links use normalized artist/title keys first, then Spotify IDs when available.
