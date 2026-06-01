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

## Implementation Concept

Use the user's supplied 24-groove conversation as the canonical seed list. Add popular reference tracks from broad groove knowledge and light research. Query the local Last.fm SQLite database by tag heuristics to propose personal candidates, but mark those as heuristic so they can be verified by ear before Spotify export.

## Development Notes

- Created `Docs/DrumGrooveStudyPlaylists.md`.
- The file has 24 playlist sections named `Drums Groove NN - Groove Name`.
- Each section includes a Spotify-ready table with `Artist` and `Title` columns.
- Seed artists were filled in where the user's source list only supplied song titles.
- Tempo is marked `verify` unless it was not safely established.
- Local Last.fm candidates are selected by tag heuristics and playcount, not by guaranteed groove transcription.

## Validation

- `bash Diagnostics/check.sh` -> pass, including 17 pytest tests.
- Manual checks:
  - 24 groove sections exist.
  - No `verify artist` placeholders remain.
  - Output file is markdown and Spotify-ready.

## User Test Instructions

1. Open `Docs/DrumGrooveStudyPlaylists.md`.
2. Review each groove section.
3. Mark any rows that should be excluded from Spotify export by changing `Use For Spotify` from `yes` to `no`.
4. Verify BPM/arrangement notes for songs you plan to practice seriously.

## Feedback And Fix History

- User supplied 24 groove categories and seed songs from a previous ChatGPT conversation.

## Closure Notes

Not closed yet.
