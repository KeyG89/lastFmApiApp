# T.9 Drum Groove Study Playlists

Status: In Progress
Commit Prefix: `[T.9]`

## Goal

Create drum-practice playlists organized by groove type, combining the user's ChatGPT seed songs, broadly known groove references, and local Last.fm candidates.

## Acceptance Criteria

- Build one markdown file with one Spotify-ready playlist section per groove.
- Each playlist section contains about 15 tracks: 5 seed tracks, 5 popular references, and 5 local Last.fm candidates where available.
- Include groove notes, tags/style, meter/grid, drummer practice focus, and conservative structure notes.
- Avoid inventing precise BPM or arrangement details when not verified.
- Keep the markdown easy to convert into Spotify playlists later.
- Add a verified export draft that excludes weak Last.fm tag matches, especially remixes, psy/trance, DnB/liquid funk, dubstep, and reggaeton false positives.
- Include a BPM value for every export row with a source/status flag so practice tempo can be reviewed before playlist creation.

## Implementation Concept

Use the user's supplied 24-groove conversation as the canonical seed list. Add popular reference tracks from broad groove knowledge and light research. Query the local Last.fm SQLite database by tag heuristics to propose personal candidates, but mark those as heuristic so they can be verified by ear before Spotify export.

After user feedback, add a stricter verification pass. Treat seed and popular references as exportable, but make local Last.fm rows opt-in: only rows explicitly verified for the groove stay Spotify-ready. Keep rejected rows in the verified draft as an audit trail.

## Development Notes

- Created `Docs/DrumGrooveStudyPlaylists.md`.
- The file has 24 playlist sections named `Drums Groove NN - Groove Name`.
- Each section includes a Spotify-ready table with `Artist` and `Title` columns.
- Seed artists were filled in where the user's source list only supplied song titles.
- Tempo is marked `verify` unless it was not safely established.
- Local Last.fm candidates are selected by tag heuristics and playcount, not by guaranteed groove transcription.
- Created `Docs/DrumGrooveStudyPlaylistsVerified.md` as the export draft.
- Added `tools/generate_drum_groove_verified.py` so the verified draft can be regenerated from the original working file.
- Replaced `Brad Sucks - Broder Line (Psy Craft Rmx)` with the local original `Brad Sucks - Borderline` only in the rock 8th notes playlist.
- Excluded liquid funk rows from funk/New Orleans/songo because liquid funk is DnB, not funk drumming.
- Excluded psy/trance/dubstep/reggaeton/generic jazz-hop false positives from local Last.fm rows unless explicitly verified.
- Added `BPM` and `BPM Source` fields to every verified row. These are practice-oriented approximations and need a metronome/chart check before serious study.

## Validation

- `bash Diagnostics/check.sh` -> pass, including 17 pytest tests.
- Manual checks:
  - 24 groove sections exist.
  - No `verify artist` placeholders remain.
  - Output file is markdown and Spotify-ready.
  - Verified export draft has 24 groove sections.
  - Known false positives are no longer Spotify-ready:
    - `Brad Sucks - Broder Line (Psy Craft Rmx)`
    - `Nero - Must Be the Feeling (Delta Heavy remix)`
    - `B Complex - Beautiful Lies`
    - `Cosmic Gate - Exploration Of Space (Hard Kandy Remix)`
  - Verified export draft reports 259 Spotify-ready rows and 101 excluded / needs-ear-check audit rows.

## User Test Instructions

1. Open `Docs/DrumGrooveStudyPlaylistsVerified.md`.
2. Use only rows where `Spotify Ready` is `yes` for Spotify export.
3. Treat `BPM Source = practice fallback` as a tempo placeholder to verify by metronome or chart.
4. Keep the original `Docs/DrumGrooveStudyPlaylists.md` as the unverified working draft.

## Feedback And Fix History

- User supplied 24 groove categories and seed songs from a previous ChatGPT conversation.
- User flagged false local matches: psytrance remixes in rock/disco, liquid funk in funk, and remix rows such as Brad Sucks `Broder Line (Psy Craft Rmx)`.
- Verification pass now keeps local Last.fm candidates conservative and auditable.

## Closure Notes

Not closed yet.
