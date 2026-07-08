# T.8 Current Music Discovery Expander

Status: In Progress
Commit Prefix: `[T.8]`

## Goal

Create a feature that takes a seed playlist vibe and generates two current-year expansion playlists: updates from known artists and discoveries from unknown/current artists.

## Acceptance Criteria

- Given a seed playlist, extract style/vibe keys from tags, artists, tracks, eras, and listening history.
- Playlist A: newer songs from the seed artists that are missing from the user's Last.fm scrobbles and Spotify playlists.
- Playlist B: newer/current songs from different artists in the same vibe, prioritizing popularity/current momentum and excluding known library items.
- Search uses current internet sources with citations and records sources in the local backlog.
- Both expansion playlists can be dry-run matched and exported to Spotify.

## Implementation Concept

Use Last.fm/Spotify local data for exclusions and identity matching. Use web research for current popularity and current releases, then write candidates to SQLite before Spotify export.

## Development Notes

- 2026-07-08: Created five current/acclaimed discovery playlists for Electronic, EDM, House, Rock, and Various Songs. The exact `artist - title` pairs were checked against the local Last.fm database before Spotify export. Research notes and source links are recorded in `Docs/DiscoveryBangers2026-07-08.md`.

## Validation

- 2026-07-08: Verified zero local scrobbles for the final 50 exact `artist - title` candidates before export.
- 2026-07-08: Spotify dry-runs matched 50/50 tracks.
- 2026-07-08: Spotify exports created five private playlists and added 50/50 tracks.

## User Test Instructions

1. Open the playlist links in `Docs/DiscoveryBangers2026-07-08.md`.
2. Listen and record feedback by playlist and track: keep, meh, wrong vibe, too obvious, too obscure, already known elsewhere, or strong discovery.
3. Use the feedback to tighten the next recommendation pass.

## Feedback And Fix History

- Awaiting user listening feedback for the 2026-07-08 discovery playlists.

## Closure Notes

Not closed yet.
