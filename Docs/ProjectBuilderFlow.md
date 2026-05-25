# Project Builder Flow

This project was created with `project-builder-flow`.

`project-builder-flow` standardizes how agent-built projects are planned, implemented, tested, documented, and improved over time. The source workflow repository is:

```text
/Users/krzysztofgoscinski/Library/code/project-builder-flow
https://github.com/KeyG89/project-builder-flow
```

## What This Means

- `MasterPlan.md` is the project source of truth.
- `Items/` contains the detailed plan and execution notes for each item.
- `Docs/` contains durable developer documentation.
- `Tutorial/` contains a consistent developer tutorial website.
- `Diagnostics/` contains readiness checks.
- `Tests/` contains automated tests, manual test notes, fixtures, or high-level validation plans.
- `AGENTS.md` tells coding agents how to work in this repo.

## Improvement Loop

Generated projects are expected to improve the workflow that created them. When the user identifies a better convention, missing scaffold, repeated fix, or stronger diagnostic, agents should propose that improvement back to `project-builder-flow` through a PR.
