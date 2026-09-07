# Change: Add a friendly projects page

## Why

Rueo.ru should give visitors a visible path to related Esperanto resources
without mixing those external projects into the four primary dictionary
sections.

## What Changes

- Add a desktop navigation item labelled `Проекты`, aligned on the right before
  the theme controls and separated from them by additional whitespace.
- Add the same destination to the mobile drawer.
- Add a `Дружественные проекты` page with bilingual Russian/Esperanto entries
  for `biologio.rueo.ru` and `frazaro.ru`.
- Make external destinations explicit, accessible, and safe to open in a new
  browser tab.

Stage II is intentionally not changed during the first local iteration. After
the Stage I page is accepted, the finished change will be ported separately to
the `feature/Stage_II` worktree.

## Impact

- Affected specs: `frontend`
- Affected code: Vue router, shared main layout, new frontend page
- No backend, database, deployment, or production changes
