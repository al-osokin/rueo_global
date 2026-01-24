# Parser and Review Spec (Stage II worktree)

This spec captures the parsing and editorial review pipeline as implemented in the Stage II worktree (`feature/Stage_II`). It is not part of Stage I production. Sources include `memory-bank/docs/Agents.md`, `memory-bank/docs/Agents.ISSUE12_CONTEXT.md`, `memory-bank/docs/MANUAL_OVERRIDE_GUIDE.md`, `memory-bank/docs/PARSER_ARCHITECTURE_NOTES.md`, and `memory-bank/tasks/*` from the Stage II branch.

## Scope and intent

- Applies to the Stage II worktree only.
- Goal: parse dictionary articles into structured JSON, generate translation candidates, and support a human review workflow.

## Architecture (Stage II)

Backend components
- `backend/app/parsing/parser_v3/text_parser.py`: character-based parser with abbreviation context handling.
- `backend/app/parsing/parser_v2.0_clean.py`: legacy parser kept for reference; earlier notes indicate some templates relied on it before refactoring.
- `backend/app/services/article_parser.py`: wraps parsing and prepares payloads.
- `backend/app/services/translation_review.py`: builds TranslationGroup objects and candidate variants.
- `backend/app/services/article_review.py`: review workflow, load/reparse/save.

Frontend component
- `frontend-app/src/pages/AdminReview.vue`: admin review UI.

Database tables
- `Article`, `ArticleRu`: raw source text.
- `ArticleParseState`: parsed_payload, resolved_translations, parsing_status.
- `ArticleParseNote`: editor notes.

## Data flow

1) Raw article text is stored in `Article.priskribo`.
2) Parser produces `parsed_payload` JSON and stores it in `ArticleParseState`.
3) `translation_review` builds TranslationGroup objects and candidates.
4) Admin review UI lets editors select candidates or enter manual overrides.
5) Decisions are saved into `resolved_translations` and used for downstream indexing.

## API endpoints (Stage II admin)

- `GET /admin/articles/{lang}/{art_id}`: fetch review payload.
- `POST /admin/articles/{lang}/{art_id}/review`: save review decisions.
- `POST /admin/articles/{lang}/{art_id}/reparse`: reparse one article.
- `POST /admin/articles/{lang}/reparse`: batch reparse by status; accepts `include_pending` and optional `art_ids` list.

## Manual override (editor input)

- Available for groups with `requires_review=true`.
- Editor enters custom translations separated by `|`.
- Stored in `resolved_translations.groups[group_id].manual_override`.
- Included in `ArticleParserService` output for full-text indexing.

## Examples vs translations

- TranslationGroup has `eo_source` field.
  - `eo_source=null`: regular translation group.
  - `eo_source=string`: example/illustration; UI should show the Esperanto source separately.

## CLI helpers (debugging)

- `backend/app/tools/review_translations.py --lang eo --offset N --limit N`.
- `ArticleReviewService.reparse_article(lang, art_id)`.
- `ArticleParserService.parse_article_by_id(lang, art_id, include_raw=True)`.
- `_get_article_sections(lang, art_id)` for fallback/debug.

## Status summary (Stage II work)

Implemented fixes documented in Stage II memory-bank:
- Duplicate elimination for numbered entries (review caching and numbered block handling).
- Reference filtering to avoid ghost groups (`_is_pure_reference_segment`).
- Example filtering for tilde-marked lines (`~` in Esperanto examples).
- Base candidate logic fixed for "As in source" variant (simple split by `,`/`;`).
- Leading adjective expansion (adj list + noun) in review processing.
- `_ili_` alternative expansion by enhancing `_PhraseBuilder.add_alternatives()`.
- Multiline translation continuation merge in parser_v3 normalization.
- Abbreviation and punctuation handling (attach `.`, `!`, `?` to previous token).
- Official marks `*N` recognized without leaking digits into translations.

Known remaining issues (documented as partial or postponed):
- Optional parts after words still need better candidate generation for UI.
- Italic notes and references can still leak into translations in some cases.

## Baseline test articles (Stage II)

These are used as regression anchors in Stage II:
- Article 270 `[aer|o]`: ~24 groups after continuation merge.
- Article 365 `[aer/trafik|o]`: 4 groups.
- Article 383 `[afekt|i]`: ~45 groups after duplicate/continuation fixes.
- Article 54 `[~igx/i]`: 1 group with 3 full translations after continuation merge.
- Article 57 `[ablativ|o]`: 4 items after `_ili_` expansion.

## Planned UI improvements (Stage II)

- Show current `art_id` near the headword and auto-fill it in the "Go to art_id" input.
- Add a range reparse UI that calls `POST /admin/articles/{lang}/reparse` with `art_ids` list.
- Display example groups (with `eo_source`) distinct from translation groups.

## Notes on parser architecture evolution

- Earlier notes flagged that several parser_v3 templates still used `legacy_parser.parse_article()`.
- Later refactoring introduced a standalone `text_parser.py` and replaced legacy calls in parser_v3 templates/normalization.
- Legacy parser remains in the repo for reference; removal is possible after full validation.
