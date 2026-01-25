## Context
The frontend currently uses Quasar CLI (webpack) via `@quasar/app`. Dev-only vulnerabilities remain in the webpack toolchain and its transitive dependencies.

## Goals / Non-Goals
- Goals: reduce dev dependency vulnerabilities, modernize the build toolchain, preserve existing Vue/Quasar runtime behavior.
- Non-Goals: UI changes, runtime dependency upgrades, major refactors.

## Decisions
- Decision: migrate to `@quasar/app-vite` and keep Quasar/Vue versions unchanged initially.
- Alternatives considered:
  - Stay on `@quasar/app` (webpack): lower change risk, but dev-chain vulnerabilities remain.
  - Move to `@quasar/app-webpack`: smaller change but weaker vuln reduction and less future-proof.

## Risks / Trade-offs
- Vite-based CLI may require newer Node versions.
- Webpack-specific config (`chainWebpack`) must be translated to Vite equivalents.
- Some dev-time linting features may change if we drop webpack ESLint plugin.

## Migration Plan
1. Confirm Node/npm versions in dev and CI.
2. Replace CLI package and adjust dev dependencies.
3. Update `quasar.config.cjs` to Vite-style config and defines.
4. Install dependencies, run audit, and build to validate.

## Implementation Notes
- Vite requires `frontend-app/index.html` instead of `src/index.template.html`.
- PWA manifest is sourced from `src-pwa/manifest.json`; output is versioned via `manifestFilename`.
- `register-service-worker` and `workbox-build` are required for PWA builds with InjectManifest.
- Early theme bootstrap is handled in `index.html` to avoid white flash before Quasar boots.
- PWA splash background is enforced by baking a dark background into `public/icons/icon-*.png`.

## Open Questions
- What Node version is used in CI/deploy builders?
- Do we want ESLint to run during dev server start, or keep it as a separate `npm run lint`?
