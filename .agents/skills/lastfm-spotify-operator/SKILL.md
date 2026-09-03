---
name: lastfm-spotify-operator
description: Set up and safely operate this repository's Last.fm, Spotify, and Shazam data workflows. Use for developer onboarding, API credentials, connection diagnostics, Last.fm history imports and enrichment, SQLite inspection, Spotify account mirroring or playlist work, and Shazam CSV imports or exports. Do not use for unrelated Python development.
---

# Last.fm Spotify Operator

Work from the repository root. Read `AGENTS.md`, `MasterPlan.md`, and the relevant item before changing project files.

## Route the task

- For installation, credentials, OAuth, or a new machine, read [references/setup.md](references/setup.md).
- For Last.fm imports, enrichment, database inspection, reports, Spotify playlists, or Shazam workflows, read [references/operations.md](references/operations.md).
- For a task spanning setup and operation, read both references before acting.

## Operational invariants

- Treat `.env`, `data/*.sqlite*`, and `data/spotify_token.json` as local secrets or user data. Never print their values, commit them, or copy them into issues, prompts, logs, or documentation.
- Ask the developer to place credentials in `.env`; do not ask them to paste credentials into chat.
- Prefer the checked-in `.venv` workflow and `.venv/bin/lastfm-app`. Do not install project packages globally.
- Inspect with `status`, a limited import, a dry run, or a limited sync before a large or external operation.
- Do not mutate Spotify merely because the user asks for analysis or a plan. Spotify writes require a request that clearly authorizes the write.
- Create private Spotify playlists unless the user explicitly requests public visibility.
- Before renaming or unfollowing a playlist, sync the account mirror and inspect protection status. Unknown, external, and pre-cutoff playlists are protected; use only the exact confirmation phrase emitted by the CLI after the user explicitly approves that target.
- Never bypass playlist protection, edit protection flags manually, or use `--no-skip-existing` without an explicit duplicate-playlist request.
- Stop on Spotify rate limiting and report the retry interval. Do not build a tight retry loop.
- Import personal Shazam history only from the CSV downloaded from Shazam on the web.
- Preserve existing databases. Do not delete, recreate, or manually rewrite them unless the user explicitly requests a repair and a backup exists.

## Completion gate

Run `bash Diagnostics/check.sh`. For integration work, also run `.venv/bin/python Diagnostics/integration_doctor.py .`. Report what was validated, what needs user-side browser authorization, and whether any command would create or alter remote Spotify data.
