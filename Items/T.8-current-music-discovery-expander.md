# T.8 Current Music Discovery Expander

Status: Open
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

No implementation yet.

## Validation

Not run yet.

## User Test Instructions

To be written after implementation.

## Feedback And Fix History

No feedback yet.

## Closure Notes

Not closed yet.
