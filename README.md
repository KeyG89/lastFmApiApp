# Last.fm API App

Python CLI + SQLite app that safely imports a user's full Last.fm listening history, enriches artists/tracks with Last.fm metadata and tags, and prepares reports for future playlist and discovery features.

This repository was created with `project-builder-flow` and follows its standard structure: `MasterPlan.md` is the source of truth, `Items/` holds item-level plans and execution notes, `Docs/` holds durable documentation, `Tutorial/` provides the developer tutorial website, and `Diagnostics/` contains readiness checks.

## Quick Start

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
cp .env.example .env
```

Fill `LASTFM_API_KEY`, `LASTFM_SHARED_SECRET`, and `LASTFM_USERNAME` in `.env`.

```bash
lastfm-app init-db
lastfm-app import-history --full
lastfm-app enrich --artists --limit 100
lastfm-app enrich --tracks --limit 250
lastfm-app report favorites --limit 30
lastfm-app report genres --limit 30
```

For a safe smoke import:

```bash
lastfm-app import-history --max-pages 1
```

## Spotify Export

Create a Spotify developer app, add this redirect URI, and put the app's client ID in `.env`:

```text
http://127.0.0.1:8765/callback
```

The local Spotify settings are:

```bash
SPOTIFY_CLIENT_ID=
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8765/callback
SPOTIFY_TOKEN_PATH=data/spotify_token.json
SPOTIFY_MARKET=PL
```

Authorize once:

```bash
.venv/bin/lastfm-app spotify auth
```

List built-in presets and dry-run matching:

```bash
.venv/bin/lastfm-app spotify presets --verbose
.venv/bin/lastfm-app spotify create --preset morning-rock-bangers --dry-run
```

Create a private playlist:

```bash
.venv/bin/lastfm-app spotify create --preset morning-rock-bangers
```

You can also create from a text file with one `Artist - Track` per line:

```bash
.venv/bin/lastfm-app spotify create --input my-playlist.txt --name "My Last.fm Playlist"
```

## Stack

Python 3.11+, stdlib HTTP client, SQLite, pytest. The app uses the official Last.fm API rather than HTML scraping.

## Data Safety

- `.env` and local databases are ignored by git.
- Imports are paginated and resumable through SQLite deduplication and cached API responses.
- Metadata enrichment is deliberately conservative; start with `--limit` before enriching everything.

## Workflow

1. Pick or create an item in `MasterPlan.md`.
2. Work in the matching `Items/T.<id>-<slug>.md` file.
3. Implement, test, update docs/tutorial, and record validation.
4. Commit with `[T.<id>] <item title>`.
5. Run `bash Diagnostics/check.sh` before closing larger items.

## Workflow Improvements

If the user identifies a change that would improve the project template, agent instructions, tutorial standard, diagnostics, GitHub automation, or item workflow, treat it as an improvement to `project-builder-flow`. Follow `AGENTS.md` and `Docs/AutoImprovement.md` to update the source workflow repo and open a PR.
