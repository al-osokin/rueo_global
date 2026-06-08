# Frontend Deployment Notes

## Current SSH target

While the normal Timeweb network path is unreliable and public `rueo.ru` is served through the emergency proxy, deploy to the origin IP directly:

```bash
./scripts/deploy_frontend_pwa.sh --apply
```

The deploy/update scripts currently default to:

```bash
SERVER_SSH=root@72.56.13.203
```

When the normal network path is fixed, revisit `SERVER_SSH_DEFAULT` in:

- `scripts/deploy_frontend_pwa.sh`
- `scripts/rueo_update.sh`

The value can still be overridden per run with `SERVER_SSH=...`.

## PWA Version Bump

Use `frontend-app/bump-version.sh <version>` instead of editing only `package.json`.

The visible PWA version is stored in several places:

- `frontend-app/package.json`
- `frontend-app/package-lock.json`
- `frontend-app/public/package.json`
- `frontend-app/src-pwa/custom-service-worker.js` (`CACHE_VERSION`)

`frontend-app/quasar.config.cjs` derives `manifestFilename` from `package.json`, but `bump-version.sh` also checks it in case it is changed back to a static filename later.

After a version bump, verify that the built `sw.js` contains the matching cache version, for example:

```bash
npm --prefix frontend-app run build -- -m pwa
grep -o 'c="vX.Y.Z"' frontend-app/dist/pwa/sw.js
```
