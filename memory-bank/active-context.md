# Active Context — rueo_global

Updated: 2026-09-08 02:39 (Europe/Moscow)

## 2026-09-08 — friendly projects mirrored from Stage I

- Mirrored the accepted Stage I `Проекты` navigation item and `/projektoj`
  page into `feature/Stage_II` after the Stage I `develop`/`master`
  realignment. The page lists Biologio and Frazaro with separate Russian and
  Esperanto descriptions and safe external links.
- The shared layout and new page match Stage I; the Stage II router retains its
  additional admin routes. Strict OpenSpec validation, targeted ESLint, and
  the Quasar 1.0.8 PWA build passed.
- Existing unrelated local work in `frontend-app/src/pages/AdminV4Review.vue`,
  `.learnings/`, and `backend/.env.lmstudio` was not modified or included in
  the feature package. No deployment or database operation was performed.

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
## 2026-06-08 — PWA news refresh cache fix ported from rueo_master

Sasha reported in the `rueo_master` context that updated prod `news.md` was not appearing in the PWA even after manual refresh and cache clearing.

Ported the local fix from `rueo_master` to avoid Stage II regression:
- `frontend-app/src/components/NewsFeed.vue`: fetch `/news.md?ts=...` with `cache: 'no-store'`, store raw source text, and detect edits by text changes rather than item count only.
- `frontend-app/src-pwa/custom-service-worker.js`: exclude `news.md` from precache and serve `/news.md` network-only.
- `frontend-app/public/.htaccess`: no-cache headers for both `sw.js`/`service-worker.js` and `news.md`.
- frontend version bumped locally to `1.0.7` to match `rueo_master` and keep PWA update detection aligned.

Verification:
- `npm --prefix frontend-app run build -- -m pwa` passed in `rueo_global`.

Prod deploy was done from `rueo_master` only after Sasha approved:
- Deployed frontend `1.0.7` to origin via `SERVER_SSH=root@72.56.13.203 ./scripts/deploy_frontend_pwa.sh --apply --skip-build`.
- Live Nginx headers were also fixed on origin for `/package.json`, `/news.md`, and `sw.js` because `.htaccess` is not active on that contour.

No commit has been made. Existing unrelated dirty Stage II files remain: `frontend-app/src/pages/AdminV4Review.vue`, `.learnings/`, `backend/.env.lmstudio`.

## 2026-06-08 — deployment default and PWA version note

Ported prod deployment defaults from `rueo_master`:
- While the Timeweb network path is unreliable and public `rueo.ru` lives behind the emergency proxy, `scripts/deploy_frontend_pwa.sh` and `scripts/rueo_update.sh` default to `SERVER_SSH=root@72.56.13.203`.
- Added `memory-bank/FRONTEND_DEPLOYMENT.md` with the current deploy channel and PWA version-bump rules.
- Important version rule: use `frontend-app/bump-version.sh <version>`; the version is not only in `package.json`, it must also be synchronized to `package-lock.json`, `public/package.json`, and `src-pwa/custom-service-worker.js` (`CACHE_VERSION`).

Follow-up local fix on 2026-06-08:
- Sasha noticed in prod that the first `#` heading in a `news.md` block rendered smaller than later `#` headings.
- Root cause was the same in Stage II: `NewsFeed.vue` extracts the first `# ...` into `item.title`, removes it from Markdown, and rendered it as `div.text-h6`.
- Ported the `rueo_master` fix: extracted news titles now render as semantic `<h1 class="news-card-title">` with the same size as Markdown `h1`, keeping only card-specific zero margin.
- Frontend version bumped locally to `1.0.8` to match `rueo_master`.
- Verification: `npm --prefix frontend-app run build -- -m pwa` passed.

News structure follow-up on 2026-06-08:
- Ported the `rueo_master` parser change for the new news file structure: `#` headings are top-level sections, `##` headings are individual news items.
- In `rueo_master`, `frontend-app/public/news.md` is an absolute symlink to `/home/avo/.rueo-shared/news.md` and is explicitly ignored by `.gitignore`; the shared news content is not part of this repo commit.
- Pagination and homepage limits count only `##` items; intro-only sections such as `ПЕРЕПИСКА` render outside the item count.
- Rendering groups visible news items under one section heading, so `#` headings are not duplicated per item.
- Homepage limit remains 5 news items; `/novajxoj` still paginates 10/20/50 items.
- Verification: `npm --prefix frontend-app run build -- -m pwa` passed.
- Not deployed.

## 2026-06-10 — old.rueo.ru update contour ported from prod

Ported the `rueo_master` legacy old.rueo.ru update contour to Stage II's `scripts/rueo_update.sh` so future Stage II work does not lose the prod dictionary update workflow.

The normal new-site dictionary update still uses:
`./scripts/rueo_update.sh run --last-ru-letter <word>`.

The old-site update remains a separate follow-up command:
`./scripts/rueo_update.sh run-old --last-ru-letter <word>`.

Order matters: run the new-site update first, then `run-old`, because the new-site pipeline syncs the dated local dictionary sources back before the old-site importer rsyncs them to `/var/www/slovari/data/www/updater.rueo.ru/src/`.

Legacy notes from the prod validation:
- `vortaro_updater.service` / port `12443` is not required for the CLI path and can remain stopped.
- `run-old` imports on origin through the legacy PHP importer, first into `slovari_vortaro_test`, then into `slovari_vortaro` after a MySQL backup.
- The live old-site `statistiko` table must be preserved. The PHP importer truncates only `artikoloj`, `artikoloj_ru`, `sercxo`, `sercxo_ru`, and `neklaraj`; do not replace this path with a full-database restore.

Verification:
- `bash -n scripts/rueo_update.sh` passed in `rueo_global`.
