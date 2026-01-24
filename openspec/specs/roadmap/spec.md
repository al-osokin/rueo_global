# Roadmap Spec

This spec captures forward-looking plans that already exist in the repo documentation. It does not introduce new design beyond those sources.

Sources
- Stage II plan: `memory-bank/03_Stage2_Full_Text_Search.md`
- Stage III plan: `memory-bank/04_Stage3_Semantic_Parsing.md`
- Background: `memory-bank/01_Initial_Task_Description.md`

## Stage II (planned): Full-text search

Goals
- Add full-text search across the full article text.
- Avoid full semantic parsing at this stage; focus on text normalization that makes search useful.

Key motivation (from `memory-bank/01_Initial_Task_Description.md`)
- Full semantic parsing is hard and may require human intervention.
- Full-text search can be useful without full parsing if normalization expands abbreviations and variants.

Planned implementation steps
- Add a new text field (example name in plan: `full_text_content`) for normalized searchable content.
- Extend the importer with text normalization steps, including:
  - tilde expansion (`~` expands to part of the headword)
  - synonym expansion for comma-separated fragments (example: "strastno, goryacho lyubit" -> multiple expanded phrases)
  - optional fragments in parentheses (example: "(lyubovnoe) uvlechenie" -> both variants)
  - removal of stress/diacritic marks and special symbols used in source markup
- Add Postgres GIN indexes on `to_tsvector(...)` for Russian and Esperanto (Esperanto may use `simple` or another appropriate config).
- Configure language-specific normalization in Postgres (examples mentioned in the plan: `yo` vs `e`, `cx` vs `c`).
- Test queries and compare result sets with the legacy search to avoid regressions.
- Add a dedicated full-text API endpoint (planned path in doc: `/api/search/full-text`) with language, pagination, and snippet support.
- Add query parameters for language filter, pagination, and sorting (relevance vs alphabetic).
- Update the frontend to support a full-text search mode with highlighted snippets and filters.
- Add logging for full-text queries (new table or extend `statistiko`).
- Update documentation and project memory after implementing.

Additional corpus plan (from Stage II doc)
- Consider indexing grammar texts in addition to dictionary entries.
- Candidate sources (outside this repo):
  - `References/rueo_fronto/src/components/gram` (Vue components)
  - `References/old.rueo.ru/tekstoj/grammatika*.textile` (legacy source files)
- When sources diverge, Vue components are considered the most up to date.
- Plan: convert grammar texts to Markdown, reuse existing Markdown support on the frontend, and index normalized text in a separate document table.
- Prefer incremental normalization based on checksums to avoid reprocessing unchanged documents.

Release checklist note (from Stage II doc)
- Before deploying a new version, verify the Orphus-style typo report flow (Ctrl+Enter). In dev environments email does not send; in prod it does.

## Stage II worktree (feature/Stage_II) - parsing and review progress

The Stage II worktree contains in-progress work on parsing and editorial review. Details are captured in `openspec/specs/parser-review/spec.md`.

Highlights
- Parser and review pipeline implemented for editor workflow (AdminReview UI, review endpoints, manual overrides).
- Parser_v3 text parser introduced to replace legacy regex splitting and handle abbreviations.
- Multiple parser/review fixes applied (duplicates, references, examples, multiline continuations, adjective lists, _ili_ alternatives, punctuation).
- Remaining issues tracked: optional parts after words (partial) and italic note leakage into translations.

Testing anchors used in Stage II
- Article 270, 365, 383 for regression checks.
- Article 54 (multiline continuation), article 57 (_ili_ alternatives), article 10 (complex notes).

## Stage III (planned): Semantic parsing and editorial admin

Goals
- Parse articles into structured semantic components.
- Provide an admin interface for human review/correction.

Planned implementation steps
- Add a `parsed_content` JSONB field and a parsing `status` field (example statuses: `raw`, `parsed`, `needs_review`).
- Run a parser across the database and collect stats.
- Choose admin UI technology (separate Vue app vs server-rendered FastAPI + Jinja2) before implementation.
- Build an editorial UI with authentication, optimized for reviewing:
  - original source text with syntax highlighting (similar to the FAR editor coloring used by maintainers)
  - a structured, human-readable representation of parsed content (not raw JSON)
- Integrate with change tracking: if a parsed article changes in source, mark it for review.
- Store hashes/snapshots for parsed articles so the importer can detect changes and reset status to `needs_review` when needed.
- Add a new API version that returns structured content (planned example path: `/api/v2/articles/{article_id}`).

Historical notes relevant to Stage III
- A prototype parser exists in legacy paths (e.g., `References/new.rueo.ru`), but parsing is ambiguous and requires human review.
- The long-term plan is to combine automatic parsing with a human review workflow to reach higher coverage.
