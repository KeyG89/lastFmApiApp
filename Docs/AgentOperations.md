# AI And Developer Operations

This repository is designed to be handed to another developer or capable coding agent without transferring local credentials or databases.

## Source Of Truth

The canonical operational skill is:

```text
.agents/skills/lastfm-spotify-operator/SKILL.md
```

It routes to focused setup and operations references. Read only the reference needed for the task, but read that selected file completely before executing commands.

## Agent Discovery

| Client | Automatically loaded entrypoint | Operational skill path |
| --- | --- | --- |
| Codex | `AGENTS.md` | `.agents/skills/lastfm-spotify-operator/` |
| Claude Code | `CLAUDE.md` | `.claude/skills/lastfm-spotify-operator/` adapter |
| Gemini CLI | `GEMINI.md` | Canonical skill linked from the context file |
| GitHub Copilot | `.github/copilot-instructions.md` and supported agent files | Canonical skill linked from its instructions |
| Other coding agents | `README.md`, then `AGENTS.md` | Open the canonical `SKILL.md` directly |

If a client does not automatically discover repository instructions, begin with:

```text
Read AGENTS.md and .agents/skills/lastfm-spotify-operator/SKILL.md completely.
Then read the relevant item file linked from MasterPlan.md and only the setup/operations reference
needed for this task. Do not expose .env, token, or database contents.
```

## Handoff Paths

- New machine or missing credentials: use the skill's `references/setup.md`.
- Import Last.fm history or enrich metadata: use `references/operations.md` → “Last.fm database import and enrichment”.
- Inspect data or answer music-history questions: use the read-only SQLite section.
- Mirror Spotify or create a playlist: use the Spotify sections and require explicit authorization for remote writes.
- Import Shazam data or prepare playlists: use the Shazam section; personal history comes from the Shazam web CSV.
- Diagnose the checkout: run `.venv/bin/python Diagnostics/integration_doctor.py .`, then `bash Diagnostics/check.sh`.

## Trust Boundaries

- Git contains code, empty configuration templates, docs, and tests.
- `.env`, Spotify tokens, SQLite databases, exports, and generated data stay local and ignored.
- A developer supplies credentials directly in their own `.env`; agents should never request credential values in chat.
- Read-only investigation does not authorize Spotify playlist creation, rename, public visibility, or unfollow operations.
- The CLI's protected-playlist confirmation and operation backlog are safety controls, not obstacles to bypass.

## Maintainer Check

When CLI flags, OAuth scopes, schema names, safety rules, or data sources change, update the canonical skill references, this runbook, README, tutorial, and diagnostics in the same item.
