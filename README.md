# Last.fm API App

Python CLI + SQLite app that safely imports a user's full Last.fm listening history, enriches artists/tracks with Last.fm metadata and tags, and prepares reports for future playlist and discovery features.

This repository was created with `project-builder-flow` and follows its standard structure: `MasterPlan.md` is the source of truth, `Items/` holds item-level plans and execution notes, `Docs/` holds durable documentation, `Tutorial/` provides the developer tutorial website, and `Diagnostics/` contains readiness checks.

## Developer And Agent Handoff

Start with [AGENTS.md](AGENTS.md) and [Docs/AgentOperations.md](Docs/AgentOperations.md). The canonical project skill is [`.agents/skills/lastfm-spotify-operator/SKILL.md`](.agents/skills/lastfm-spotify-operator/SKILL.md); it contains routed setup and operations references for Last.fm, Spotify, Shazam, SQLite, reports, and playlist workflows.

- Codex discovers the canonical skill under `.agents/skills/`.
- Claude Code loads `CLAUDE.md` and the adapter under `.claude/skills/`.
- Gemini CLI loads `GEMINI.md`.
- GitHub Copilot loads `.github/copilot-instructions.md` in supported clients.
- Other coding agents can read `AGENTS.md` and the canonical skill directly.

Validate a handoff without displaying credential values:

```bash
.venv/bin/python Diagnostics/integration_doctor.py .
bash Diagnostics/check.sh
```

## Quick Start

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
cp .env.example .env
```

Fill `LASTFM_API_KEY` and `LASTFM_USERNAME` in `.env`. `LASTFM_SHARED_SECRET` is optional for the current read-only Last.fm methods.

```bash
.venv/bin/lastfm-app init-db
.venv/bin/lastfm-app import-history --full
.venv/bin/lastfm-app enrich --artists --limit 100
.venv/bin/lastfm-app enrich --tracks --limit 250
.venv/bin/lastfm-app report favorites --limit 30
.venv/bin/lastfm-app report genres --limit 30
```

For a safe smoke import:

```bash
.venv/bin/lastfm-app import-history --max-pages 1
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
SPOTIFY_MAX_RATE_LIMIT_SLEEP_SECONDS=15
```

Authorize once:

```bash
.venv/bin/lastfm-app spotify auth
```

Re-run auth whenever Spotify scopes change. The current app asks for playlist read/modify, library read/modify, top artists/tracks, and recently played scopes.

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

Mirror Spotify playlists into SQLite:

```bash
.venv/bin/lastfm-app spotify sync --limit 10 --delay 3
.venv/bin/lastfm-app spotify playlists
```

Safety rule: playlists created by this app on or after `2026-05-31` are editable by the app. Synced playlists with unknown creation dates are treated as protected. Rename/unfollow/delete-style operations on protected playlists require an exact `--confirm` phrase printed by the CLI.

The CLI uses Spotify Authorization Code with PKCE, so it needs the client ID but no client secret. See the skill's [setup reference](.agents/skills/lastfm-spotify-operator/references/setup.md) for current dashboard, redirect URI, scope, and troubleshooting details.

## Shazam Library

Shazam data is stored in a separate local SQLite database, `data/shazam.sqlite3` by default. The supported source is the CSV downloaded from Shazam on the web. The import preserves Shazam `TrackKey`, normalized artist/title keys, the Shazam URL, tag time, and raw source rows so the data can later be matched against Last.fm, Spotify, or web research. Linked Shazam tracks can be enriched with local Last.fm tags for genre and energy grouping.

```bash
.venv/bin/lastfm-app shazam init
.venv/bin/lastfm-app shazam import <path-to-shazam.csv> --link-lastfm
.venv/bin/lastfm-app shazam enrich-lastfm
.venv/bin/lastfm-app shazam status
```

Generate local playlist plans from all imported Shazams:

```bash
.venv/bin/lastfm-app shazam playlists --show
```

The all-track playlist is sorted from most energetic to least energetic. Genre playlists are generated to cover the whole imported Shazam library. Unknown or weakly-classified tracks go to `Shazam: Various`.

Create the generated Shazam playlists on Spotify and record the created playlist IDs/URLs locally:

```bash
.venv/bin/lastfm-app shazam export-spotify --show
.venv/bin/lastfm-app shazam export-spotify --no-match --delay 10 --show
.venv/bin/lastfm-app shazam spotify-exports
```

## Stack

Python 3.11+, stdlib HTTP client, SQLite, pytest. The app uses the official Last.fm API rather than HTML scraping.

## Data Safety

- `.env` and local databases are ignored by git.
- Spotify access/refresh tokens stay in the ignored `data/spotify_token.json` cache.
- Imports are paginated and resumable through SQLite deduplication and cached API responses.
- Metadata enrichment is deliberately conservative; start with `--limit` before enriching everything.
- Spotify playlist creation defaults to private; analysis or planning does not authorize remote writes.

## Workflow

1. Pick or create an item in `MasterPlan.md`.
2. Work in the matching `Items/T.<id>-<slug>.md` file.
3. Implement, test, update docs/tutorial, and record validation.
4. Commit with `[T.<id>] <item title>`.
5. Run `bash Diagnostics/check.sh` before closing larger items.

For operational work, use the `lastfm-spotify-operator` skill and keep its setup/operations references synchronized with CLI changes.

## Workflow Improvements

If the user identifies a change that would improve the project template, agent instructions, tutorial standard, diagnostics, GitHub automation, or item workflow, treat it as an improvement to `project-builder-flow`. Follow `AGENTS.md` and `Docs/AutoImprovement.md` to update the source workflow repo and open a PR.
