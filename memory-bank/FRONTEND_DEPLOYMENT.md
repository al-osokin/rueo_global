# Frontend Deployment Notes

## Current SSH target

Production `rueo.ru` is now served from the FirstVDS Stage host. The deploy/update scripts use the local SSH alias by default:

```bash
./scripts/deploy_frontend_pwa.sh --apply
```

Current default:

```bash
SERVER_SSH=firstvds-stage
```

If the SSH alias changes, revisit `SERVER_SSH_DEFAULT` in:

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
