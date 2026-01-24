# Data Pipeline Spec

This spec covers the import/update pipeline that refreshes the dictionary database and generates deployed status files.

Primary references
- Importer: `backend/app/importer.py`.
- Article tracking: `backend/app/services/article_tracking.py`.
- Automation script: `scripts/rueo_update.sh`.
- Operator notes: `memory-bank/07_Update_Automation_Jan2026.md`, `memory-bank/Automated DB update.md`, `memory-bank/08_Fix_Dump_Issues_Jan2026.md`.

## Inputs

### Source dumps
- Default input root: `backend/data/src/` (`DEFAULT_DATA_DIR` in `backend/app/importer.py`).
- Expected per-language directories:
  - Esperanto: `backend/data/src/VortaroER-daily/`
  - Russian: `backend/data/src/VortaroRE-daily/`
- Importer reads `.txt` files and decodes them as cp1251.

### Control file: last RU letter
- `backend/data/src/last-ru-letter.txt` (optional).
  - Used as a "last ready RU word" marker for status reporting.
  - May be updated by the importer.

### Optional overrides
- `RUEO_DATA_DIR` can override the default input directory (used by the importer).

## Importer stages (backend/app/importer.py)

### 1) Initialize
- Calls `init_db()` to ensure tables exist.
- Resolves `run_time`:
  - argument `--run-at` / `run_at`
  - or env `RUEO_IMPORT_RUN_AT`
  - or current time

### 2) Truncate tables (optional)
- Default behavior truncates core dictionary tables before loading.
- Tables truncated by `_truncate_tables(...)`:
  - `sercxo`, `sercxo_ru`, `artikoloj`, `artikoloj_ru`, `neklaraj`

### 3) Parse and load articles
- Reads each `.txt` file from the language directory.
- Detects structural issues in the source file (header/word alignment) and reports them via a callback.
- Writes raw article bodies into:
  - Esperanto: `artikoloj`
  - Russian: `artikoloj_ru`

### 4) Article tracking and auto-dating
- Tracking tables (see `backend/app/models.py`):
  - `article_file_states`
  - `article_states`
  - `article_change_log`
- The pipeline stores per-article checksums so it can detect meaningful changes.
- For RU sources, the importer may rewrite the original `.txt` file (still cp1251) when it needs to update header date lines for changed articles. This is why the update pipeline includes a "sync-back" step.
- A previous update date is derived from `backend/data/tekstoj/renovigxo.md` when present.

### 5) Build search index tables
- Rebuilds `sercxo` (eo) and `sercxo_ru` (ru) by tokenizing article headers.
- For RU, also adds a variant with `yo` replaced (implemented in code).

### 6) Build fuzzy table
- Rebuilds `neklaraj` by deriving fuzzy pairs from `sercxo`.

### 7) Generate status files
Written under `backend/data/tekstoj/`:
- `klarigo.md` (human-readable summary)
- `renovigxo.md` (update history; prepends a new entry)
- `tracking-summary.json` (machine-readable tracking summary)

## Automation script (scripts/rueo_update.sh)

The script is the operator-facing wrapper around the end-to-end update + deployment workflow. It includes subcommands:
- `run` (full pipeline)
- `sync-in` (copy Dropbox sources into `backend/data/src`)
- `import-local` (run importer locally)
- `sync-back` (copy back importer-modified source files)
- `dump-local-db` (create a Postgres custom-format dump)
- `restore-server-db` (upload and restore the dump on the server)
- `deploy-tekstoj` (copy `klarigo.md` and `renovigxo.md` to the server)
- `reset-tracking` (truncate tracking tables)

Database URL resolution (from memory-bank)
- `dump-local-db` resolves `DATABASE_URL` in this order:
  1) `DATABASE_URL` env var if set
  2) `docker exec rueo_backend printenv DATABASE_URL`
  3) default `postgresql://rueo_user:rueo_password@localhost:5432/rueo_db`
- `restore-server-db` reads the server `DATABASE_URL` from the backend container on the server.
- The URL parser is tolerant of special characters (for example `?`) in passwords.

Restore behavior (from memory-bank)
- Terminates active connections to the target DB before restore.
- Uses `pg_restore --clean --if-exists --no-owner --no-privileges`.

Operational intent (from `memory-bank/07_Update_Automation_Jan2026.md`)
- Preferred approach is "import locally, then dump/restore to server":
  1) sync sources from Dropbox to local `backend/data/src`
  2) run importer locally
  3) sync-back any importer-edited source files (auto-dated headers)
  4) create local DB dump (custom format)
  5) upload dump and restore on server (no importer run on server)
  6) deploy `backend/data/tekstoj/klarigo.md` and `backend/data/tekstoj/renovigxo.md`

Important environment variables (names only; do not document secrets)
- Source sync: `DROPBOX_VORTARO_RE`, `DROPBOX_VORTARO_ER`
- File permissions: `NORMALIZE_PERMS=0` to disable chmod
- Import: `IMPORT_CMD`, `RUEO_IMPORT_RUN_AT`
- DB access: `DATABASE_URL`, `LOCAL_PG_CONTAINER`, `LOCAL_BACKEND_CONTAINER`
- Server deployment: `SERVER_SSH`, `SERVER_TEKSTOJ_DIR`, `SERVER_PG_CONTAINER`, `SERVER_BACKEND_CONTAINER`

Default container names (from scripts)
- Local Postgres: `rueo_postgres`
- Local backend: `rueo_backend`
- Server Postgres: `rueo-db-1`
- Server backend: `rueo-backend-1`

## Operator runbook (short)

Typical update
1) `./scripts/rueo_update.sh run --last-ru-letter <word>`
2) If `--last-ru-letter` is omitted, the script prompts and defaults to `backend/data/src/last-ru-letter.txt`.

Key paths and side effects
- Local dump path: `backend/tmp/rueo_db_<UTC>.dump`
- Server tekstoj path: `/var/www/slovari/data/www/rueo.ru/backend/data/tekstoj/`
- Source sync examples (from memory-bank):
  - `/mnt/f/Backup/Dropbox/VortaroRE-daily` -> `backend/data/src/VortaroRE-daily`
  - `/mnt/f/Backup/Dropbox/VortaroER-daily` -> `backend/data/src/VortaroER-daily`
- The script removes `*:com.dropbox.attrs` artifacts if they appear and normalizes permissions to 755/644 unless disabled.
- `sync-back` keeps exclusion patterns for `*:com.dropbox.attrs` and `*.attrs` as a safety net.

## Baseline run for tracking (run_at override)

Purpose: rebuild tracking baseline aligned to a specific historical update date.
- Mechanism: CLI `--run-at` and env `RUEO_IMPORT_RUN_AT` feed `run_time` used by tracking logic.
- Example sequence (concept only): reset tracking tables, then run importer with `RUEO_IMPORT_RUN_AT=YYYY-MM-DD`.

Reset tracking behavior
- `reset-tracking` truncates tracking tables with `RESTART IDENTITY CASCADE`.
- Target tables: `article_change_log`, `article_states`, `article_file_states`.

## Dump/restore robustness (Jan 2026 notes)

From `memory-bank/08_Fix_Dump_Issues_Jan2026.md`:
- The update script added checks to ensure required Docker containers are actually running (not just existing).
- The script validates parsed `DATABASE_URL` components before running `pg_dump`.
- The script verifies dump creation and `docker cp` steps and fails fast with actionable errors.
- Server restore checks also verify the server Postgres container is running.

## Operator quick checks

- `backend/data/tekstoj/tracking-summary.json` includes per-language counts such as:
  - `articles_changed`
  - `articles_auto_dated`
  - `articles_new`
- If the importer edited RU source files (auto-dating), ensure "sync-back" ran successfully or the next "sync-in" will revert changes.

## Legacy state import (optional tooling)

`backend/app/tools/import_dictionary_states.py` imports historical JSON state into the tracking tables.
It expects a directory of `*.json` files and can optionally reset existing state for a language.
