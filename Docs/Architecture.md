# Architecture

Project kind: `python`.

The app is a local data pipeline with a thin CLI:

- `src/lastfm_app/cli.py`: command surface for import, enrichment, status, and reports.
- `src/lastfm_app/lastfm.py`: official Last.fm API client with retry/backoff.
- `src/lastfm_app/importer.py`: pagination, scrobble parsing, metadata enrichment, and API cache usage.
- `src/lastfm_app/db.py`: SQLite connection, schema, upserts, tag normalization, and aggregate stats.
- `src/lastfm_app/reports.py`: local summaries used as the first playlist intelligence layer.

Generated databases live under `data/` by default and are ignored by git. Secrets live in `.env`, never in tracked files.
