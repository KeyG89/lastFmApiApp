# T.7 Shazam Library Integration

Status: In Progress
Commit Prefix: `[T.7]`

## Goal

Add Shazam-derived music signals so discovered songs can be mapped into the Last.fm and Spotify data model.

## Acceptance Criteria

- Define the source path for Shazam data: CSV downloaded from Shazam on the web.
- Store Shazam tracks, artists, timestamps, source metadata, and match confidence in a dedicated local SQLite database.
- Link Shazam tracks to Spotify tracks and Last.fm tracks where possible.
- Expose CLI commands to import Shazam data and show unmatched discoveries.
- Generate one all-Shazam playlist sorted from calmest to most energetic.
- Generate genre/tag playlists that cover the imported Shazam library.

## Implementation Concept

Use the CSV downloaded from Shazam on the web as the source of truth. There is no usable public network route for the user's personal Shazam history in this project, so remove the earlier network-import code and keep enrichment/search through Last.fm, Spotify, and web research as later steps keyed by normalized artist/title and Shazam track keys.

Create a separate `data/shazam.sqlite3` database by default. Keep raw imported source rows for auditability, then derive playlist candidates from normalized artist/title, imported genres/tags, optional Spotify matches, and simple energy heuristics.

## Development Notes

- 2026-05-31: User requested local Shazam database, all-track calm-to-energetic playlist, and genre playlists covering all Shazams.
- Implemented `src/lastfm_app/shazam.py` with a dedicated SQLite schema, Shazam web CSV import, Shazam track keys, Last.fm linking, Spotify matching, Shazam status, and playlist generation.
- CLI commands added under `lastfm-app shazam`: `init`, `import`, `status`, `link-lastfm`, `match-spotify`, and `playlists`.
- Tutorial HTML, architecture docs, README, `.env.example`, and diagnostics now document the Shazam path.
- 2026-06-01 feedback superseded the earlier network-import experiment: user confirmed only the downloaded Shazam web CSV is viable. Removed those unused Shazam import paths.

## Validation

- `.venv/bin/python -m pytest -q` -> 16 passed after the CSV-only correction.
- `bash Diagnostics/check.sh` -> pass, including Last.fm and Shazam diagnostics.
- Imported `/Users/krzysztofgoscinski/Downloads/shazamlibrary.csv`: 191 CSV rows seen, 159 unique Shazam tracks stored, 39 linked to Last.fm, 22 enriched with local Last.fm tags.
- Generated Shazam playlists: 7 playlists, 318 playlist item rows.

## User Test Instructions

1. Download the Shazam library CSV from Shazam on the web.
2. Run `.venv/bin/lastfm-app shazam init`.
3. Run `.venv/bin/lastfm-app shazam import /Users/krzysztofgoscinski/Downloads/shazamlibrary.csv --link-lastfm`.
4. Run `.venv/bin/lastfm-app shazam match-spotify --limit 25` after the Spotify rate-limit window clears.
5. Run `.venv/bin/lastfm-app shazam playlists --show`.

## Feedback And Fix History

- User later verified that the personal Shazam history path is only the downloaded web CSV.

## Closure Notes

Not closed yet.
