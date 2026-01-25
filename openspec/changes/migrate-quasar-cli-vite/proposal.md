# Change: Migrate Quasar CLI to Vite

## Why
Reduce dev dependency vulnerabilities and align with the supported Quasar CLI tooling while improving build performance and maintenance.

## What Changes
- Replace `@quasar/app` with `@quasar/app-vite`.
- Update `quasar.config.cjs` for Vite-specific configuration (define injection, optional lint integration).
- Adjust dev dependencies and lockfile for the Vite toolchain.
- Update developer docs where they reference the tooling.
- Move HTML template to `frontend-app/index.html` and add early theme bootstrap.
- Introduce `src-pwa/manifest.json` and versioned `manifest-<version>.json` output.
- Update PWA splash assets to use a dark background for consistent startup visuals.

## Impact
- Affected specs: frontend
- Affected code: `frontend-app/package.json`, `frontend-app/package-lock.json`, `frontend-app/quasar.config.cjs`, `frontend-app/index.html`, `frontend-app/src-pwa/manifest.json`, `frontend-app/public/icons/*`, `frontend-app/src-pwa/custom-service-worker.js`, `frontend-app/bump-version.sh`, `frontend-app/README.md`
- **Potential breaking**: Node version requirements for Vite-based CLI (verify dev/CI).
