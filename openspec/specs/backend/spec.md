# Backend Spec

This spec documents the FastAPI backend behavior as implemented in Stage I.

Primary code references
- Routes: `backend/app/main.py`, `backend/app/admin.py`.
- Search: `backend/app/services/search.py`.
- Importer: `backend/app/importer.py`.
- Article tracking: `backend/app/services/article_tracking.py`.
- DB and models: `backend/app/database.py`, `backend/app/models.py`.

Verification note
- Requests/responses below are derived from code inspection and memory-bank docs.
- No commands were executed as part of this documentation run.

## Service contract

### Base
- Default local port (Compose): `8000` (see `docker-compose.yml`).
- All endpoints are mounted at the root (no `/api` prefix in Stage I).

### Content types
- `GET` endpoints respond with JSON.
- `POST /orph` accepts `application/x-www-form-urlencoded` form fields.
- `POST /admin/import` accepts JSON.

## Endpoints

### GET /
Serves the legacy SPA entrypoint if it exists; otherwise returns a small JSON message.
- Code: `backend/app/main.py`.

### GET /admin/ui
Serves `frontend/admin.html` if present.

Responses
- `200`: file response.
- `404`: JSON error if the file is missing.

### GET /status/info
Returns a text blob describing the latest dictionary update.

Inputs
- None.

Behavior
- Reads `backend/data/tekstoj/klarigo.md` (required).
- Optionally reads the first non-empty line of `backend/data/tekstoj/renovigxo.md` and prefixes it.

Responses
- `200`: `{ "text": "..." }`.
- `404`: if `klarigo.md` is missing.

### GET /search
Dictionary search.

Query parameters
- `query` (string, required, min length 1)

Behavior (high-level)
- Normalizes Esperanto input to internal `ux` digraphs (see `backend/app/utils/esperanto.py`).
- Detects language heuristically (Latin initial -> `eo`, else `ru`).
- Searches the language-specific `sercxo`/`sercxo_ru` index tables.
- Logs searches into `statistiko` (hashed client IP when available).
- Returns server-rendered HTML snippets for the frontend to inject.

Response
`200` JSON:
- `count` (int)
- `html` (string): rendered HTML for the SPA to inject
- `fuzzy_html` (string): extra "similar words" HTML

Search matching strategy (from code + memory-bank)
- Exact variants are tried first (case variants, hyphen, roman numerals, quoted form, << >> markers).
- If no exact match, a regex prefix search is used.
- If still no results, a LIKE fallback is used.
- Fuzzy suggestions are returned from `neklaraj` as HTML links.

HTML formatting rules (format_article in `backend/app/services/search.py`)
- `[...]` marks headword blocks and is rendered as strong text.
- `<...>` and `<word@label>` patterns become links when the word exists, otherwise blue spans.
- `{...}` blocks are rendered in italic green as notes; underscores denote italic blocks.
- `*` markers and `*<n>` markers render as green star badges.
- Backtick accent marks are converted into combining stress marks.
- Various legacy replacements are applied to preserve original PHP formatting behavior.

### GET /suggest
Autocomplete suggestions.

Query parameters
- `term` (string, required, min length 1)

Behavior
- Similar normalization and language detection as `/search`.
- Returns up to 30 unique suggestions (querying up to 60 DB rows).

Response
`200` JSON array of objects:
- `id` (int): article id
- `label` (string)
- `value` (string)

### POST /orph
User feedback endpoint (typo report / "Orphus").

Form fields
- `url` (string, required)
- `text` (string, required): error text
- `comment` (string, optional, default empty)
- `key` (string, required): shared secret

Authorization
- Compares `key` to the `RUEO_ORPH_KEY` environment variable (with a built-in fallback). Do not hardcode this value in docs.

Side effects
- Appends a text entry to `backend/data/logs/orph.txt` (best-effort).
- Sends an email using SMTP settings from environment variables (best-effort).

Responses
- `200`: `{ "status": "ok" }`
- `400`: missing required fields
- `403`: invalid key

### POST /admin/import
Triggers an import run in the background.

Request JSON
```json
{
  "data_dir": "optional path; default is backend/data/src",
  "truncate": true,
  "last_ru_letter": "optional string"
}
```

Notes
- `data_dir` is a filesystem path interpreted by the backend process. Prefer leaving it unset in normal operation.
- The import is scheduled as a FastAPI background task and does not block the request.
- The importer exposes per-stage progress callbacks used by the admin status response.

Responses
- `202` JSON (import status object):
  - `running` (bool)
  - `last_started` (string, ISO timestamp, nullable)
  - `last_finished` (string, ISO timestamp, nullable)
  - `last_error` (string, nullable)
  - `progress` (object, nullable)
  - `stats` (object, nullable)
  - `last_ru_letter` (string, nullable)
- `400`: when the data directory does not exist
- `409`: when an import is already running

### GET /admin/import/status
Returns the current import status.

Responses
- `200`: same shape as the `202` body from `POST /admin/import`.

## Data flow (request path)

### Search and suggest
1) `backend/app/main.py` route handler obtains a DB session.
2) `backend/app/services/search.py` runs queries against `sercxo`/`sercxo_ru`.
3) HTML is generated server-side from stored article text and returned to the frontend.

### Import and tracking
1) `POST /admin/import` schedules `run_import(...)` from `backend/app/importer.py`.
2) Importer loads source dumps from `backend/data/src/` (cp1251 `.txt`).
3) Importer truncates and rebuilds tables, then writes `backend/data/tekstoj/*` status files.
4) Article tracking logic stores checksums and can auto-update header date lines for changed articles (tracking tables in `backend/app/models.py`).
5) The in-process admin state is updated via a callback (see `backend/app/admin.py`).

## Bootstrap admin user (implementation detail)
- On first init, `init_db()` creates tables and then ensures a default admin user exists.
- The username and password are hardcoded in code. Do not publish the password value; treat this as a dev/bootstrap mechanism only.

## Historical notes (Stage I progress, Oct 2024)
- The importer and search stack were validated with `python -m compileall backend/app` without errors after fixing `__pycache__` permission issues.
- Import status reporting includes stages for file processing, index rebuild, and fuzzy-table updates (surface area exposed via `/admin/import/status`).
