# Auto-Improvement Workflow

Use this file when the user says that something in this project should become part of the standard workflow for future projects.

## Trigger

Create a `project-builder-flow` improvement when the user points to:

- a missing or weak default in generated projects;
- a repeated manual step;
- a better agent instruction;
- a better item/MasterPlan convention;
- a better diagnostics or testing pattern;
- a better tutorial UI/content pattern;
- a bug in the generator or skill.

## Required Steps

1. Update this project's `MasterPlan.md` under `Workflow Improvements` with the improvement idea.
2. Go to `/Users/krzysztofgoscinski/Library/code/project-builder-flow`.
3. Create a new item or update an existing item in `project-builder-flow/MasterPlan.md`.
4. Create or update the matching `project-builder-flow/Items/T.<id>-<slug>.md`.
5. The item must include:
   - source project: `lastfmapiapp`;
   - user request or observed problem;
   - exact functionality to add/change;
   - files/templates/docs likely affected;
   - acceptance criteria;
   - validation plan.
6. Create a branch:

```bash
git checkout -b improvement/lastfmapiapp-<short-slug>
```

7. Implement the improvement in `project-builder-flow`.
8. Run:

```bash
bash Diagnostics/check.sh
.venv/bin/python /Users/krzysztofgoscinski/.codex/skills/.system/skill-creator/scripts/quick_validate.py skill/project-builder
python3 scripts/install_skill.py
```

9. Commit with the matching item prefix, for example:

```bash
git commit -m "[T.5] Improve Generated Project Auto-Improvement Contract"
```

10. Push and open a PR to `main`.

## PR Description Template

```markdown
## Summary
- Source project: lastfmapiapp
- User request / observed problem:
- Functionality added or changed:

## Project Builder Flow Updates
- MasterPlan item:
- Item file:
- Templates/docs/scripts changed:

## Validation
- [ ] bash Diagnostics/check.sh
- [ ] skill validator on skill/project-builder
- [ ] generated project smoke test

## Migration Notes
- Existing generated projects:
```
