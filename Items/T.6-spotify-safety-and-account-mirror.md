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
- `spotify sync` supports `--playlist-id`, `--limit`, and `--delay` so the account mirror can be built in controlled batches.
- Non-owned playlists are skipped before track fetches to avoid Spotify `403 Forbidden` responses.
- Spotify `429` responses now fail fast when `Retry-After` is long and are logged as rate-limit events instead of silently sleeping.

## Validation

- Unit tests cover protected playlist policy.
- Unit tests cover long Spotify rate-limit handling.
- Real Spotify auth now has the expanded scopes, but track sync is currently blocked by Spotify API rate limiting after repeated full-sync attempts.

## User Test Instructions

1. After the Spotify rate-limit window clears, run `.venv/bin/lastfm-app spotify sync --playlist-id 7g57arQ36vxBFFnQXWBZqS --delay 2`.
2. If that succeeds, run `.venv/bin/lastfm-app spotify sync --limit 10 --delay 3`.
3. Run `.venv/bin/lastfm-app spotify playlists`.
4. Try a protected rename without `--confirm`; it should be blocked and logged.

## Feedback And Fix History

- 2026-05-31: User hit `403 Forbidden` while syncing tracks; sync now skips non-owned playlists.
- 2026-05-31: User hit Spotify `429 Too Many Requests`; sync now reports the retry window clearly and stops instead of appearing hung.

## Closure Notes

Not closed yet.
