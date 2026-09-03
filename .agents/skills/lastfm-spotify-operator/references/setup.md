# Integration Setup

Use this reference for a new clone, a new developer, missing credentials, or failed Last.fm/Spotify authorization.

## Contents

- Local environment
- Last.fm application
- Spotify application and PKCE login
- Shazam source
- Readiness checks
- Troubleshooting

## Local environment

Requirements: Git, Python 3.11 or newer, and a browser for Spotify OAuth.

```bash
gh repo clone KeyG89/lastFmApiApp
cd lastFmApiApp
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
cp .env.example .env
```

If `.env` already exists, preserve it. Never overwrite or commit it. The CLI loads `.env` automatically when run from the repository root.

## Last.fm application

1. Sign in to Last.fm and create an API application at <https://www.last.fm/api/account/create>.
2. Put the API key and target Last.fm username in the local `.env`:

   ```dotenv
   LASTFM_API_KEY=
   LASTFM_USERNAME=
   ```

3. `LASTFM_SHARED_SECRET` may remain empty for the current read-only `user.getRecentTracks`, `artist.getInfo`, `artist.getTopTags`, `track.getInfo`, and `track.getTopTags` workflows. Store it only in `.env` if a future signed Last.fm method needs it.
4. Keep the default request delay unless a task justifies a more conservative value:

   ```dotenv
   LASTFM_REQUEST_DELAY_SECONDS=0.25
   ```

Validate without a full import:

```bash
.venv/bin/lastfm-app init-db
.venv/bin/lastfm-app import-history --max-pages 1
.venv/bin/lastfm-app status
```

The import is idempotent at the scrobble level: repeated track/timestamp rows are ignored.

## Spotify application and PKCE login

The CLI uses Authorization Code with PKCE and does not need a Spotify client secret.

1. Create an app in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
2. In the app settings, register this redirect URI exactly:

   ```text
   http://127.0.0.1:8765/callback
   ```

   Use `127.0.0.1`, not `localhost`. Spotify permits HTTP for explicit loopback IP addresses and requires the authorization request URI to match the registered URI.
3. Add only the client ID to `.env`:

   ```dotenv
   SPOTIFY_CLIENT_ID=
   SPOTIFY_REDIRECT_URI=http://127.0.0.1:8765/callback
   SPOTIFY_TOKEN_PATH=data/spotify_token.json
   SPOTIFY_MARKET=PL
   SPOTIFY_MAX_RATE_LIMIT_SLEEP_SECONDS=15
   ```

4. Authorize interactively:

   ```bash
   .venv/bin/lastfm-app spotify auth
   ```

   For a remote shell, use `--no-browser`, open the printed URL in a browser, and ensure the callback can reach port `8765` on the machine running the CLI.

The token cache contains access and refresh tokens and must remain under ignored `data/`. Re-run auth after scopes change or when the CLI reports insufficient scope. The app currently requests playlist read/write, library read/write, top-items, and recently-played scopes.

Official references:

- [Spotify app setup](https://developer.spotify.com/documentation/web-api/concepts/apps)
- [Redirect URI requirements](https://developer.spotify.com/documentation/web-api/concepts/redirect_uri)
- [Authorization Code with PKCE](https://developer.spotify.com/documentation/web-api/tutorials/code-pkce-flow)
- [Spotify scopes](https://developer.spotify.com/documentation/web-api/concepts/scopes)

## Shazam source

Shazam needs no API credential in this project. Download the personal library CSV from Shazam on the web and keep it outside Git.

The importer requires recognizable artist and title columns. It also accepts common optional columns such as `TrackKey`, `TagTime`, album, genre, Shazam URL, and Apple Music URL. Validate a file with:

```bash
.venv/bin/lastfm-app shazam init
.venv/bin/lastfm-app shazam import <path-to-shazam.csv> --link-lastfm
.venv/bin/lastfm-app shazam status
```

## Readiness checks

Run both checks from the repository root:

```bash
.venv/bin/python Diagnostics/integration_doctor.py .
bash Diagnostics/check.sh
```

The integration doctor reports presence and validity, never credential contents. Missing credentials are setup warnings; broken tracked agent assets, unsafe paths, malformed token JSON, and invalid redirect configuration are failures.

## Troubleshooting

- `LASTFM_API_KEY is required`: populate `.env` and run from the repository root.
- Spotify `INVALID_CLIENT`: verify `SPOTIFY_CLIENT_ID` against the selected dashboard app.
- Spotify redirect mismatch: register the exact `.env` URI, including scheme, IP, port, path, and trailing slash behavior.
- Spotify insufficient scope: run `spotify auth` again and approve the requested scopes.
- Spotify `403`: confirm the authenticated account can access the developer app and that the playlist is owned by that account.
- Spotify `429`: stop and wait for the reported `Retry-After`; do not repeatedly retry.
- Missing Shazam rows: confirm the input is a CSV with artist and title columns, then inspect `shazam_import_runs` as described in `operations.md`.
