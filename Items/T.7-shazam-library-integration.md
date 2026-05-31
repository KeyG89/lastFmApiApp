# T.7 Shazam Library Integration

Status: In Progress
Commit Prefix: `[T.7]`

## Goal

Add Shazam-derived music signals so discovered songs can be mapped into the Last.fm and Spotify data model.

## Acceptance Criteria

- Define the source path for Shazam data: Shazam/RapidAPI search, Spotify API playlist import, or fallback export file.
- Store Shazam tracks, artists, timestamps, source metadata, and match confidence in a dedicated local SQLite database.
- Link Shazam tracks to Spotify tracks and Last.fm tracks where possible.
- Expose CLI commands to import Shazam data and show unmatched discoveries.
- Generate one all-Shazam playlist sorted from calmest to most energetic.
- Generate genre/tag playlists that cover the imported Shazam library.

## Implementation Concept

Use API-backed import first. There is no confirmed public Apple endpoint for downloading the user's complete Shazam history as a web API response, so support two API routes: Shazam/RapidAPI search/details for Shazam catalog lookups, and Spotify playlist import for the user's synced `My Shazam Tracks` playlist when available. Keep CSV/JSON as a fallback only.

Create a separate `data/shazam.sqlite3` database by default. Keep raw imported source rows for auditability, then derive playlist candidates from normalized artist/title, imported genres/tags, optional Spotify matches, and simple energy heuristics.

## Development Notes

- 2026-05-31: User requested local Shazam database, all-track calm-to-energetic playlist, and genre playlists covering all Shazams.
- Official personal Shazam-history API availability is not assumed. The supported API paths are Shazam/RapidAPI catalog search and Spotify API playlist import.
- Implemented `src/lastfm_app/shazam.py` with a dedicated SQLite schema, Shazam API import, Spotify playlist API import, CSV/JSON fallback import, Last.fm linking, Spotify matching, Shazam status, and playlist generation.
- CLI commands added under `lastfm-app shazam`: `init`, `api-check`, `api-search`, `import-spotify-playlist`, `import`, `status`, `link-lastfm`, `match-spotify`, and `playlists`.
- Tutorial HTML, architecture docs, README, `.env.example`, and diagnostics now document the Shazam path.
- 2026-05-31 feedback: user rejected CSV/JSON as the main path. Added explicit Shazam API/RapidAPI integration and Spotify playlist API import.

## Validation

- `.venv/bin/python -m pytest -q` -> 16 passed.
- `bash Diagnostics/check.sh` -> pass, including Last.fm and Shazam diagnostics.
- Smoke-tested Shazam CLI import/status/playlists with a temporary CSV and temporary SQLite database.

## User Test Instructions

1. Add `SHAZAM_RAPIDAPI_KEY` to `.env` if using direct Shazam API search.
2. Run `.venv/bin/lastfm-app shazam api-check`.
3. Import through API with `.venv/bin/lastfm-app shazam api-search "artist track" --limit 5`.
4. If Shazam is synced to Spotify, import the Spotify `My Shazam Tracks` playlist with `.venv/bin/lastfm-app shazam import-spotify-playlist PLAYLIST_ID --link-lastfm`.
5. Run `.venv/bin/lastfm-app shazam playlists --show`.

## Feedback And Fix History

- User clarified that API integration is required and CSV/JSON alone is not acceptable.

## Closure Notes

Not closed yet.
