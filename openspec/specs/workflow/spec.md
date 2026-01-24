# Workflow Spec

This spec documents the Stage I vs Stage II workflow rules used for this project.

Primary references
- `memory-bank/docs/WORKFLOW.md`
- `memory-bank/tasks/_TEMPLATE.md`

## Worktrees and branches

- Stage I (prod): `~/rueo_master` on `master`.
- Stage II (stage/experimental): `~/rueo_global` on `feature/Stage_II`.

Guiding rule
- Stage I is the source of truth for anything that powers the current production site.

## What must match between Stage I and Stage II

Derived from `memory-bank/docs/WORKFLOW.md`:
- Import of raw dictionary text into the DB (cp1251 `.txt` ingestion, core tables).
- The backend API used by the current site (search/suggest/status/orph/admin import).
- Shared models/schema behavior and deployment mechanics.

## What may differ in Stage II

- Parser logic and related services used to build full-text / semantic indexes.
- Experimental disambiguation logic and analysis tools.

## Backport policy

When a change affects shared/prod behavior:
1) Implement it in Stage I first.
2) Immediately backport into Stage II (prefer `git cherry-pick`, or merge).

When a change is Stage II-specific:
- Implement only in Stage II.
- Do not backport into Stage I until there is an explicit decision to promote it.

## Documentation discipline (lightweight)

For non-trivial changes, the project uses lightweight plan files under `memory-bank/tasks/`.

Template highlights (English summary of `memory-bank/tasks/_TEMPLATE.md`)
- Title and date, branch targets (Stage I + Stage II)
- Why: pain point and motivation
- What: 1-5 concrete behavior changes
- Scope: affected modules/files (backend, frontend, scripts)
- Acceptance criteria checklist
- Plan checklist:
  1) Prepare/design the solution
  2) Implement in Stage I
  3) Verify locally (commands/cases)
  4) Backport to Stage II (cherry-pick)
  5) Verify in Stage II
  6) Record result and SHAs
- Notes section for decisions/plan changes
- Verification section (commands, cases)
- Backport section (Stage I commit SHA, Stage II cherry-pick SHA)
- Result summary
