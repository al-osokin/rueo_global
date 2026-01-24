# Proposing changes

This repo uses a lightweight, file-based process to make changes discoverable and easy to backport between Stage I and Stage II.

## Where to write change notes

- For non-trivial work, add a plan file under `memory-bank/tasks/` using:
  - `memory-bank/tasks/_TEMPLATE.md`

## What to include

- Why: the problem and impact.
- What: concrete behavior changes.
- Scope: key files and modules.
- Verification: how to validate the change.
- Backport: whether the change must be applied to Stage II and how.

## Stage I vs Stage II rules

Follow `memory-bank/docs/WORKFLOW.md`:
- Shared/prod fixes go to Stage I first, then backport to Stage II.
- Experimental parser/full-text work stays in Stage II until promoted.

## OpenSpec updates

If a change affects system behavior, update the relevant OpenSpec files under `openspec/` (this directory) so the specs stay aligned with the code.
