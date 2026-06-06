# Master / Global sync audit

Created: 2026-06-06

## Goal

Carefully compare `rueo_master` (prod / Stage I) and `rueo_global` (Stage II) before finalizing prod commits, so prod fixes/content changes are not lost when Stage II becomes primary.

## Working rule

- Treat `rueo_master` as the source for prod fixes already deployed or verified on rueo.ru.
- Treat `rueo_global` as active Stage II development; do not overwrite its local logic changes blindly.
- For every `rueo_master` change, decide one of:
  - port directly to `rueo_global`;
  - mark as prod-only with a reason;
  - investigate because `rueo_global` changed the relevant logic.

## Suggested audit steps

1. Confirm both worktrees share the expected base commits:
   - `git -C /home/avo/rueo_master log --oneline --decorate -8`
   - `git -C /home/avo/rueo_global log --oneline --decorate -8`
2. Inventory uncommitted changes separately:
   - `git -C /home/avo/rueo_master status --short`
   - `git -C /home/avo/rueo_global status --short`
3. Compare tracked source paths, excluding generated/local/memory paths first:
   - frontend app source and public files;
   - backend app source, scripts, tests;
   - config/templates that affect runtime behavior.
4. For each diff, classify it as:
   - commit drift: a prod fix/content update missing from `rueo_global`;
   - Stage II intentional divergence: logic changed in `rueo_global`;
   - local/generated/noise: ignore or document.
5. Port only the commit-drift changes, then run targeted tests/builds in the affected tree.
6. Commit in small groups, including relevant `memory-bank/*` updates with the code change.

## Current known sync item

- 2026-06-06: `frontend-app/public/mecenatoj.txt` patron-list correction from `rueo_master` was ported to `rueo_global`.
