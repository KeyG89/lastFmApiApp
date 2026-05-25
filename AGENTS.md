# Agent Instructions

This project was created with `project-builder-flow`.

Source workflow repo:

```text
/Users/krzysztofgoscinski/Library/code/project-builder-flow
https://github.com/KeyG89/project-builder-flow
```

## Project Work

- Start every task by reading `MasterPlan.md` and the relevant file in `Items/`.
- If there is no item for the user request, create one before implementation.
- Keep statuses current: `Open`, `In Progress`, `Done`.
- Commit project work as `[T.<item>] <item title>`.
- Keep docs, diagnostics, and the developer tutorial updated when behavior changes.
- Keep secrets out of git; use `.env.example`.

## Auto-Improvement Contract

When the user points to something in this project that should improve future projects, do not treat it as a one-off local tweak. Treat it as a `project-builder-flow` improvement candidate.

Examples:

- better default files or directories;
- better `MasterPlan.md` or item conventions;
- better `AGENTS.md` instructions;
- better tutorial UI or content;
- better diagnostics, tests, GitHub auth, secret handling, or environment isolation;
- repeated manual steps that should become generator behavior.

Required behavior:

1. Record the idea under `Workflow Improvements` in this project's `MasterPlan.md`.
2. Open `/Users/krzysztofgoscinski/Library/code/project-builder-flow`.
3. Create or update the relevant item in that repo's `MasterPlan.md` and `Items/`.
4. Implement the improvement in the workflow repo, not only in this generated project.
5. Run the workflow repo diagnostics and skill validation.
6. Create a branch and PR to `KeyG89/project-builder-flow` with a detailed functionality description.

Read `Docs/AutoImprovement.md` for the exact PR checklist.

Project name: `Lastfmapiapp`
Project kind: `python`
