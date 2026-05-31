# T.6 Spotify Safety And Account Mirror

Status: In Progress
Commit Prefix: `[T.6]`

## Goal

Mirror the user's Spotify account into SQLite and enforce a hard safety policy for playlist mutations.

## Acceptance Criteria

- Any Spotify playlist created before 2026-05-31, or with unknown creation date, is protected.
- Protected playlist rename/edit/unfollow/delete operations require an exact explicit confirmation phrase.
- Playlists created by this app on or after 2026-05-31 are editable without extra confirmation.
- Every Spotify operation writes an entry to `spotify_operation_backlog`.
- SQLite stores Spotify account, playlists, artists, albums, tracks, playlist tracks, and Spotify-to-Last.fm links.
- CLI can sync Spotify playlists/tracks and list local playlist protection status.

## Implementation Concept

Use conservative local policy because Spotify playlist objects do not expose a reliable creation timestamp for arbitrary existing playlists. Treat synced external playlists as protected by default, while app-created playlists are recorded locally with creation time and marked editable.

## Development Notes

- Initial schema and operation backlog are implemented in `src/lastfm_app/spotify.py`.
- CLI commands added: `spotify sync`, `spotify playlists`, `spotify rename`, and `spotify unfollow`.
- Spotify scopes now include playlist read scopes and library/top/recent scopes for future features.

## Validation

- Unit tests cover protected playlist policy.
- `spotify sync` currently returns `Insufficient client scope` until Spotify auth is re-run with the expanded scope set.

## User Test Instructions

1. Run `.venv/bin/lastfm-app spotify auth` again to grant expanded scopes.
2. Run `.venv/bin/lastfm-app spotify sync`.
3. Run `.venv/bin/lastfm-app spotify playlists`.
4. Try a protected rename without `--confirm`; it should be blocked and logged.

## Feedback And Fix History

No feedback yet.

## Closure Notes

Not closed yet.
