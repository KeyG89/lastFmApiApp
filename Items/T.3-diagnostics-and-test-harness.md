# T.3 Diagnostics And Test Harness

Status: Done
Commit Prefix: `[T.3]`

## Goal

Create the diagnostics and automated checks that make the project safe to change.

## Acceptance Criteria

- `Diagnostics/check.sh` runs structural diagnostics, Last.fm diagnostics, and pytest.
- `Diagnostics/lastfm_doctor.py` verifies local DB setup and reports secret presence without printing values.
- Tests cover scrobble parsing, duplicate imports, stats recomputation, and tag parsing.

## Implementation Concept

Use pytest for fast parser/database tests and shell diagnostics for project readiness.

## Development Notes

- Added `Tests/test_importer.py`.
- Updated CI to install `.[dev]` before running diagnostics.

## Validation

- `bash Diagnostics/check.sh` passed.

## User Test Instructions

Run `bash Diagnostics/check.sh`.

## Feedback And Fix History

No feedback yet.

## Closure Notes

Closed with the current alpha diagnostics and test harness.
