# Project: Rueo Dictionary

This OpenSpec set documents the current state of the Rueo.ru dictionary codebase (Stage I / prod) and the planned next stages.

Scope and sources
- Primary source of truth: the code in this repo.
- Historical/extended notes: `memory-bank/*` and `frontend-app/memory-bank/*` (legacy plans and context).

Repository context
- Workspace path: `/home/avo/rueo_master`.
- Stage I (prod): this repo/worktree on branch `master`.
- Stage II (stage/experimental): separate worktree `~/rueo_global` on branch `feature/Stage_II` (see `memory-bank/docs/WORKFLOW.md`).

What Rueo provides today (Stage I)
- Public dictionary API served by FastAPI:
  - `GET /search`
  - `GET /suggest`
  - `GET /status/info`
  - `POST /orph`
- Admin/import API:
  - `POST /admin/import`
  - `GET /admin/import/status`
  - `GET /admin/ui`
- Web UI:
  - Primary UI: `frontend-app/` (Vue 3 + Quasar, PWA).
  - Legacy minimal UI: `frontend/` (static HTML served by the backend).

Historical context (from memory-bank)
- The legacy production site was a 20+ year PHP/CodeIgniter + MariaDB system hosted under old.rueo.ru.
- Dictionary sources are cp1251 `.txt` files; the legacy importer was a PHP script invoked by a Python runner per file to avoid timeouts.
- The dictionary is updated on a regular cadence (roughly every 6 days) by importing full source dumps for both directions.
- A Vue + Quasar frontend (rueo_fronto in older repos) originally routed requests to old.rueo.ru and enabled PWA install.
- Stage I replaces the legacy backend with Python/FastAPI/PostgreSQL while keeping the same HTML-returning API contract.
- Stage II focuses on full-text search via normalized text without full semantic parsing.
- Stage III focuses on semantic parsing with human review.

Technology stack (as implemented)
- Backend: Python + FastAPI (`backend/app/main.py`).
- DB: PostgreSQL via SQLAlchemy (`backend/app/database.py`, `backend/app/models.py`).
- Local dev/runtime: Docker Compose (`docker-compose.yml`).
- Update automation: `scripts/rueo_update.sh`.
- Frontend app: Vue 3 + Quasar (`frontend-app/`).
- Server edge: nginx reverse-proxy for API paths (`memory-bank/docs/DEPLOYMENT_NOTES.md`).

Key paths
- Backend app entrypoint: `backend/app/main.py`.
- Admin endpoints: `backend/app/admin.py`.
- Importer: `backend/app/importer.py`.
- Search logic: `backend/app/services/search.py`.
- Article tracking: `backend/app/services/article_tracking.py`.
- Update pipeline script: `scripts/rueo_update.sh`.
- Structure checker: `scripts/check_structure_issues.py` - validates source files without full import.
- Compose (local): `docker-compose.yml`.
- Memory bank: `memory-bank/*`, `frontend-app/memory-bank/*`.

Data conventions that matter
- Source dictionary dumps are read from `backend/data/src/` (`DEFAULT_DATA_DIR` in importer).
- Source `.txt` files are decoded as cp1251 in the importer.
- Esperanto letters are normalized between accented letters (UI) and `ux` digraphs (internal) in `backend/app/utils/esperanto.py`.
- Article headers include date/author lines; the pipeline can auto-update dates if content changes and the author forgot to update the date (tracking tables).
- The importer can rewrite RU source files for auto-dating, so `sync-back` is required to avoid losing those edits.

Operational conventions
- Do not document or commit secrets. Runtime values come from env vars (`DATABASE_URL`, SMTP settings, `RUEO_ORPH_KEY`).
- `init_db()` creates a bootstrap admin user; treat it as dev-only and do not publish the password value.
- For Stage I vs Stage II workflow rules, follow `memory-bank/docs/WORKFLOW.md`.

Ops snapshot (from `memory-bank/active-context.md`)
- As of 2026-01-14, the dictionary update ran up to RU word "predstavitelstvo".
  - RU articles: 59590 (changed 24, auto-dated 23, new 10)
  - EO articles: 46460 (changed 10, auto-dated 0, new 5)
- Database was transferred to server via dump/restore; `klarigo.md` and `renovigxo.md` were deployed.
- `scripts/rueo_update.sh` received fixes for container-running checks and `DATABASE_URL` validation.
- Open TODO in that snapshot: optimize search if needed.
