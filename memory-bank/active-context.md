# Active Context — rueo_global

Updated: 2026-05-16 01:35 (Europe/Moscow)

## Current governing workflow
- Primary task contour for `rueo_global` / Stage II is now YouTrack project `eoru` / **Словари**.
- Workflow rules are saved in `memory-bank/YOUTRACK_WORKFLOW.md`.
- Assistant-created development tasks must be explicitly set to:
  - `Type`: `Задание` / `Task`
  - `State`: `Открыта` / `Open`
  - `Subsystem`: `Движок ST II`
- Project memory is handoff/research context, not an independent backlog. If memory implies executable work, use YouTrack first and keep memory as a pointer.

## Cross-worktree sync rule
- `rueo_master` is prod / Stage I, while this tree is Stage II development.
- Be very careful with commits in `rueo_master`: before committing prod changes, check whether each change must also be ported here to avoid Stage II regressions.
- Do not assume a `rueo_master`-only fix is complete unless it is deliberately prod-only; apply or explicitly record the corresponding `rueo_global` change first.
- Sasha explicitly reminded this on 2026-06-06 after the prod dictionary update to `призвание`.
- Audit plan saved in `memory-bank/MASTER_GLOBAL_SYNC_AUDIT.md`.

## 2026-05-16 — YouTrack migration from accumulated memory

Created Stage II issues from accumulated `memory-bank` notes:
- `eoru-1415` — `[ST II] L0 + model arbitration for ambiguous RU translation blocks`.
- `eoru-1416` — `[ST II] Finish parser_v4 hard-case validation and mini-regression`.
- `eoru-1417` — `[ST II] Route parser_v4 review flags to Gemma/manual review flow`.
- `eoru-1418` — `[ST II] Resume /admin/review-v4 validation pass on shortlist cases`.
- `eoru-1423` — `[ST II] Resolve parser_v4 snapshot smoke mismatch`.

All five were verified via YouTrack API as:
- `Type`: `Task`
- `State`: `Open`
- `Subsystem`: `Движок ST II`

Support file:
- `/home/avo/clawd/research/youtrack/rueo_memory_to_youtrack.py`

Detailed old task/research notes were moved out of the live backlog to:
- `memory-bank/archive/youtrack-migrated-2026-05-16/`

Live backlog is YouTrack now; archived files are evidence/context only.

## Recent technical context preserved from earlier handoff

### AdminV4 / parser_v4 stability
- `review-v4` had been stabilized so AST reads saved `parsed_payload`, with explicit `Переразобрать статью`.
- Added reset actions:
  - article-level reset;
  - block-level reset via `POST /admin/v4/reset-block`.
- Apply/reset persistence was fixed via ORM `flag_modified` on JSON fields.
- Previous reported checks:
  - parser/admin backend tests passed;
  - frontend build succeeded.

### Parser quality direction
- Current direction is to reduce unsafe L0 heuristics and move ambiguous cases to structured model arbitration (`eoru-1415`).
- Hard-case validation and regression fixture work is tracked in `eoru-1416`.
- Routing from parser_v4 flags (`clean`, `line-merge-risk`, `many-to-many`) into model/manual review is tracked in `eoru-1417`.
- Human-in-the-loop shortlist pass in `/admin/review-v4` is tracked in `eoru-1418`.

### Confirmed parser rules from memory
- `;` is a reliable sense separator.
- `_или_` / `aux` branches alternatives.
- `_см._` / `_ср._` are reference notes, not senses/translations.
- Direct brackets without a preceding space are intra-word variants: `(с)делать`, `орангутан(г)`.
- Direct brackets with a preceding space are optional word/segment variants: `анализ (крови)`.
- Italic parentheses are usually labels/notes, not translation tokens.
- RU→EO multiline merge: final `,`, `;`, or `.` is a strong line-ending signal; otherwise the next line may need merging.
- For dirty/truncated fragments, prefer `incomplete/manual review` over unsafe auto-normalization.

## Current status
- Stage II memory backlog has been moved into YouTrack issues `eoru-1415`–`eoru-1418` and `eoru-1423`.
- Detailed research files were archived under `memory-bank/archive/youtrack-migrated-2026-05-16/`; `memory-bank/tasks/` is no longer the live backlog.
- There is an uncommitted new `memory-bank/YOUTRACK_WORKFLOW.md` and updated `memory-bank/active-context.md`; do not commit without Sasha’s confirmation.
- Current additional caution: `rueo_master` may contain prod/content changes that need mirroring into this Stage II tree before any commit is finalized.
- 2026-06-06: `frontend-app/public/mecenatoj.txt` patron-list correction from `rueo_master` was ported here.

## Next step when resuming Stage II
1. Open the relevant YouTrack issue first.
2. If doing hands-on validation with Sasha, start with `eoru-1418`.
3. If doing implementation, likely start with `eoru-1415` or `eoru-1416` depending on whether the focus is architecture or fixture-backed parser fixes.
