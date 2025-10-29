# Agents Notes for rueo_global

## Project snapshot
- Repository: Esperanto→Russian dictionary backend (FastAPI) + Quasar frontend.
- Articles already live in PostgreSQL (`Article`, `ArticleRu`); parsing/review services load them through SQLAlchemy `SessionLocal`.
- Default DB URL (when running locally): `postgresql://rueo_user:rueo_password@localhost:5432/rueo_db`.

## Common CLI helpers
- Translation preview (respecting app imports):
  ```bash
  PYTHONPATH=backend python backend/app/tools/review_translations.py --lang eo --offset 100 --limit 5
  ```
- Reparse a single article (refreshes parsed JSON + review payload):
  ```bash
  PYTHONPATH=backend python - <<'PY'
  from app.database import SessionLocal, init_db
  from app.services.article_review import ArticleReviewService

  init_db()
  with SessionLocal() as session:
      ArticleReviewService(session).reparse_article('eo', 205)
  PY
  ```
- Batch reparse via API: `POST /admin/articles/{lang}/reparse` with `{ "include_pending": true|false }`.
- Single-article API reparse (used by admin UI button):
  ```
  POST /admin/articles/{lang}/{art_id}/reparse
  ```
  Returns refreshed `ArticleReviewPayload` and optional `parse_error`.

## Parser gotchas
- `parse_illustration` splits EO/RU by first Cyrillic run; beware of strings starting with punctuation (e.g. `(воз)`). Added guard so illustrations beginning with non-letters stay with surrounding translation.
- `_expand_parenthetical_forms` now normalises spaces before optional segments: `... (воз)действие` expands to `… действие | … воздействие`.
- `_apply_source_fallback` splits section text by `;`/`,` outside parentheses and auto-expands parentheses when only one spec is present; this fixes cases like `[~ec/o]`.
- `_merge_plain_russian_illustrations` converts orphan Russian examples back into translation blocks; conversion runs for blocks whose `eo` part is empty or non-alphabetic.

## Frontend/admin tips
- Admin review page expects backend running; “Переразобрать открытую” calls the single-article reparse endpoint. If you adjust parsing logic, reparse target articles so the UI reflects changes.
- The review table stores previous decisions in `article_parse_state.resolved_translations`; clearing via `POST /admin/articles/{lang}/{art_id}/reset`.

## Troubleshooting
- If Python scripts cannot import `app`, ensure commands run with `PYTHONPATH=backend`.
- For compile-time sanity checks after parser edits:
  ```bash
  PYTHONPATH=backend python -m compileall backend/app/parsing/parser_v2.0_clean.py backend/app/services/translation_review.py
  ```

Keep this file short but updated with workflow-critical knowledge so future sessions can ramp quickly.
