# T.7 Shazam Library Integration

Status: In Progress
Commit Prefix: `[T.7]`

## Goal

Add Shazam-derived music signals so discovered songs can be mapped into the Last.fm and Spotify data model.

## Acceptance Criteria

- Define the source path for Shazam data: export file, Apple Music/Shazam export, or supported local API route.
- Store Shazam tracks, artists, timestamps, source metadata, and match confidence in a dedicated local SQLite database.
- Link Shazam tracks to Spotify tracks and Last.fm tracks where possible.
- Expose CLI commands to import Shazam data and show unmatched discoveries.
- Generate one all-Shazam playlist sorted from calmest to most energetic.
- Generate genre/tag playlists that cover the imported Shazam library.

## Implementation Concept

Start with file import rather than assuming an official Shazam API. Normalize artist/title strings through the same key strategy used by Spotify and Last.fm. Use Spotify matching as the first API-backed enrichment route because it supplies durable IDs, album/release metadata, external URLs, and popularity without relying on unofficial Shazam scraping.

Create a separate `data/shazam.sqlite3` database by default. Keep raw imported source rows for auditability, then derive playlist candidates from normalized artist/title, imported genres/tags, optional Spotify matches, and simple energy heuristics.

## Development Notes

- 2026-05-31: User requested local Shazam database, all-track calm-to-energetic playlist, and genre playlists covering all Shazams.
- Official Shazam API availability is not assumed. The supported first path is CSV/JSON export import plus Spotify API matching as enrichment.
- Implemented `src/lastfm_app/shazam.py` with a dedicated SQLite schema, CSV/JSON import, Last.fm linking, Spotify matching, Shazam status, and playlist generation.
- CLI commands added under `lastfm-app shazam`: `init`, `import`, `status`, `link-lastfm`, `match-spotify`, and `playlists`.
- Tutorial HTML, architecture docs, README, `.env.example`, and diagnostics now document the Shazam path.

## Validation

- `.venv/bin/python -m pytest -q` -> 14 passed.
- `bash Diagnostics/check.sh` -> pass, including Last.fm and Shazam diagnostics.
- Smoke-tested Shazam CLI import/status/playlists with a temporary CSV and temporary SQLite database.

## User Test Instructions

1. Export Shazam discoveries to CSV or JSON.
2. Run `.venv/bin/lastfm-app shazam init`.
3. Run `.venv/bin/lastfm-app shazam import path/to/shazam.csv --link-lastfm`.
4. Run `.venv/bin/lastfm-app shazam playlists --show`.
5. After the Spotify API rate-limit window clears, run `.venv/bin/lastfm-app shazam match-spotify --limit 25`.

## Feedback And Fix History

No feedback yet.

## Closure Notes

Not closed yet.
