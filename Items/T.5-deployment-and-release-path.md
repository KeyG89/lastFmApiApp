# T.5 Spotify Playlist Export

Status: In Progress
Commit Prefix: `[T.5]`

## Goal

Create Spotify integration that can authorize the local CLI and publish Last.fm-derived playlists directly to the user's Spotify account.

## Acceptance Criteria

- Spotify auth uses Authorization Code with PKCE and stores tokens only in ignored local files.
- CLI can list built-in playlist presets made from the current Last.fm experiments.
- CLI can match preset or text-file tracks against Spotify search.
- CLI can create private Spotify playlists and add matched tracks.
- Dry-run mode shows matches without creating anything.
- Tests cover playlist parsing and match scoring.

## Implementation Concept

Use Spotify Web API with PKCE for local CLI auth. Add a lightweight stdlib client for `/authorize`, `/api/token`, `/v1/search`, `/v1/me/playlists`, and `/v1/playlists/{id}/items`. Keep Spotify credentials in `.env` and token cache under ignored `data/`.

## Development Notes

- Built-in presets cover the electronic rediscover, less-obvious electronic, and morning rock banger experiments.
- Spotify search matches by exact-ish artist and track names and stores results in a local `spotify_track_matches` table.

## Validation

Pending final smoke tests.

## User Test Instructions

1. Create a Spotify developer app and set redirect URI to `http://127.0.0.1:8765/callback`.
2. Add `SPOTIFY_CLIENT_ID` to `.env`.
3. Run `.venv/bin/lastfm-app spotify auth`.
4. Run `.venv/bin/lastfm-app spotify create --preset morning-rock-bangers --dry-run`.
5. Remove `--dry-run` to create the playlist.

## Feedback And Fix History

No feedback yet.

## Closure Notes

Not closed yet.
