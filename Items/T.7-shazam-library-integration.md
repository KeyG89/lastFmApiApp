# T.7 Shazam Library Integration

Status: Open
Commit Prefix: `[T.7]`

## Goal

Add Shazam-derived music signals so discovered songs can be mapped into the Last.fm and Spotify data model.

## Acceptance Criteria

- Define the source path for Shazam data: export file, Apple Music/Shazam export, or supported local API route.
- Store Shazam tracks, artists, timestamps, source metadata, and match confidence in SQLite.
- Link Shazam tracks to Spotify tracks and Last.fm tracks where possible.
- Expose CLI commands to import Shazam data and show unmatched discoveries.

## Implementation Concept

Start with file import rather than assuming an official Shazam API. Normalize artist/title strings through the same key strategy used by Spotify and Last.fm.

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
