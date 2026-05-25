# T.1 Last.fm Importer Alpha

Status: Done
Commit Prefix: `[T.1]`

## Goal

Create a Python CLI + SQLite app that safely imports the user's full Last.fm listening history, enriches artists/tracks with Last.fm metadata and tags, and prepares reports for future playlist and discovery features.

## Acceptance Criteria

- `lastfm-app init-db` creates the SQLite schema.
- `lastfm-app import-history --full` imports paginated Last.fm scrobbles and deduplicates repeated runs.
- `lastfm-app enrich --artists/--tracks --limit N` stores Last.fm metadata and tags.
- `lastfm-app report favorites` and `lastfm-app report genres` print useful local summaries.
- `.env` and generated databases are not committed.
- Automated tests and diagnostics pass.

## Implementation Concept

Use a small stdlib-first Python package with `argparse`, `urllib`, and SQLite. Keep API calls conservative, cached, and resumable. Normalize artists/tracks/albums into relational tables while retaining selected raw JSON for later schema evolution.

## Development Notes

- Implemented package under `src/lastfm_app`.
- Added SQLite schema, importer, Last.fm client, enrichment routines, reports, CLI, diagnostics, and tests.

## Validation

- `.venv/bin/python -m pytest -q` passed: 3 tests.
- `bash Diagnostics/check.sh` passed.
- CLI smoke checks passed for `init-db`, `status`, `report favorites`, and `report genres` against temporary SQLite databases.

## User Test Instructions

1. Copy `.env.example` to `.env` and fill `LASTFM_API_KEY`, `LASTFM_SHARED_SECRET`, and `LASTFM_USERNAME`.
2. Run `.venv/bin/lastfm-app init-db`.
3. Run `.venv/bin/lastfm-app import-history --max-pages 1` for a smoke import.
4. Run `.venv/bin/lastfm-app import-history --full` for the full history.
5. Run enrichment in batches, for example `.venv/bin/lastfm-app enrich --artists --limit 100`.

## Feedback And Fix History

No feedback yet.

## Closure Notes

Closed with the first local importer, enrichment, reporting, diagnostics, and documentation baseline implemented.
