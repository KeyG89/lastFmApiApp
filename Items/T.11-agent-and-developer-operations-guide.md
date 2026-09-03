# T.11 Agent And Developer Operations Guide

Status: Done
Commit Prefix: `[T.11]`

## Goal

Make the private repository immediately operable by another developer or a top-tier coding agent, including safe setup of Last.fm, Spotify, and Shazam integrations, database imports, reports, playlist planning, and Spotify export.

## Acceptance Criteria

- The repository contains a discoverable project-local skill with concise routing and maintained operational references.
- Codex, Claude, and other coding agents receive a clear repository entrypoint without duplicating the operational source of truth.
- A new developer can bootstrap an isolated environment, configure credentials without committing secrets, validate connections, import Last.fm and Shazam data, inspect the databases, generate reports, and plan or execute Spotify playlist exports.
- Spotify mutation instructions preserve the project's mirror-first, dry-run-first, and protected-playlist safety rules.
- README, developer tutorial, diagnostics, and agent guidance point to the same commands and remain consistent.
- The skill passes the bundled skill validator and the full project diagnostic passes.

## Implementation Concept

Add a canonical skill under `.agents/skills/lastfm-spotify-operator/` with conditional setup and operations references. Add lightweight Codex and Claude discovery links plus a model-neutral operations runbook. Update project onboarding and diagnostics so missing agent-operability assets fail clearly.

## Development Notes

- Keep all credentials in `.env`; commit only empty variable names and setup guidance.
- Derive commands and safety invariants from the implemented CLI and current project documentation.
- Added the canonical `lastfm-spotify-operator` skill under `.agents/skills` with progressive setup and operations references plus Codex UI metadata.
- Added a Claude project-skill adapter and repository entrypoints for Claude Code, Gemini CLI, GitHub Copilot, and model-neutral agents.
- Added a credential-safe integration doctor that verifies Last.fm readiness, Spotify redirect/token/scopes, untracked database paths, and agent onboarding assets.
- Updated README, architecture, workflow, test notes, `.env.example`, project diagnostics, and the developer tutorial.

## Validation

- Canonical Codex/cross-agent skill: `quick_validate.py` -> `Skill is valid!`.
- Claude skill adapter: `quick_validate.py` -> `Skill is valid!`.
- `.venv/bin/python Diagnostics/integration_doctor.py .` -> all local integration and onboarding checks passed without displaying credential values.
- Fresh-checkout simulation without `.env`, token, or databases -> expected setup warnings, no failures, and all agent entrypoints present.
- `bash Diagnostics/check.sh` -> all structural, integration, Last.fm, Shazam, secret, and CI checks passed; `23 passed` in pytest.
- `git diff --check` -> passed.
- Tutorial source structure and responsive reuse were reviewed; browser rendering was unavailable because no browser backend was connected to the session.

## User Test Instructions

1. Clone the private repository with `gh repo clone KeyG89/lastFmApiApp`.
2. Read `AGENTS.md`, `Docs/AgentOperations.md`, and `.agents/skills/lastfm-spotify-operator/SKILL.md`.
3. Create `.venv`, install `.[dev]`, copy `.env.example` to `.env`, and add credentials locally.
4. Run `.venv/bin/python Diagnostics/integration_doctor.py .`.
5. Run a one-page Last.fm import and a Spotify playlist dry run using the skill references.
6. In Codex invoke `$lastfm-spotify-operator`; in Claude Code invoke `/lastfm-spotify-operator`.

## Feedback And Fix History

Created from the request to make the private repository ready for another developer and capable coding agents.

## Closure Notes

Completed on 2026-09-03. The repository now carries its own cross-agent operational knowledge, deterministic readiness checks, and safe handoff path for music data and playlist work.
