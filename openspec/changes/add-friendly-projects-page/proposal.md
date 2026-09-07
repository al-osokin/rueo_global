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

The accepted Stage I change is mirrored in this Stage II tree. Existing Stage
II work outside the shared navigation, router, new page, and this proposal is
left untouched.

## Impact

- Affected specs: `frontend`
- Affected code: Vue router, shared main layout, new frontend page
- No backend, database, deployment, or production changes
