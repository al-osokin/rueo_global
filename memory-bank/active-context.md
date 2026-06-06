# Active Context — rueo.ru / YouTrack cleanup

Updated: 2026-06-06 04:29 (Europe/Moscow)

## Where we are
- Рабочий проект: `~/rueo_master` (prod / Stage I + dictionary update pipeline).
- Primary task contour for rueo work is now YouTrack project `eoru` / **Словари**.
- Sasha wants to return after `/new` to think about how to bring the dictionary YouTrack project into order.
- Workflow rules saved in `memory-bank/YOUTRACK_WORKFLOW.md`.

## YouTrack workflow rules

Assistant-created development/infrastructure tasks must set fields explicitly, not rely on defaults:
- `Type`: `Задание` / `Task`
- `State`: `Открыта` / `Open`
- `Subsystem`:
  - `Движок` for prod / Stage I / `rueo_master` engine work;
  - `Движок ST II` for Stage II / `rueo_global`;
  - `Инфраструктура` for YouTrack/mailbox/Reformal/import cleanup automation.

ST I can be indicated in the title (`[ST I]`) if useful; no separate ST I subsystem is needed.

## Created YouTrack issues from memory/research

### Stage I / prod / `Движок`
- `eoru-1419` — Decommission legacy `statistiko` request-statistics contour.
- `eoru-1420` — Harden `rueo_update` DB restore after `statistiko` duplicate failure.
- `eoru-1421` — Review `/search` dry-run rate-limit observations and decide enforcement policy.
- `eoru-1422` — `[ST I] Finalize patron-list frontend changes after deploy`.

### Infrastructure / `Инфраструктура`
- `eoru-1424` — Reformal cleanup helper: preview/apply for boilerplate feedback issues.
- `eoru-1425` — Reformal threads: collapse reply issues into the root feedback issue.
- `eoru-1426` — Reformal/mailbox import policy: avoid standalone issues for replies/comments.

### Stage II / see `~/rueo_global`
- `eoru-1415`–`eoru-1418`, `eoru-1423` are Stage II / `Движок ST II` tasks.

All newly created issues were checked via API as `Task` / `Open` with intended subsystems.

Support files:
- `/home/avo/clawd/research/youtrack/rueo_memory_to_youtrack.py`
- `/home/avo/clawd/research/youtrack/reformal-cleanup-workflow-notes.md`
- `/home/avo/clawd/research/youtrack/eoru-youtrack-inventory-2026-05-15.md`

## Reformal cleanup context

Reformal/mailbox import problem:
- incoming Reformal feedback creates HTML-heavy generic YouTrack tasks;
- Reformal threaded correspondence becomes multiple standalone issues.

Test fixture:
- `eoru-1380` — root Reformal feedback about `tio` vs `ĝi` / PMEG.
- `eoru-1381`–`eoru-1384` — replies/comments belonging to that root.
- Sasha moved all five to `Исправление не планируется` / `Won't fix`, intentionally did not delete them, so they can be used to test `eoru-1425` safely.

Desired helper behavior:
- read-only inventory first;
- parse HTML and extract Reformal user/profile, feedback URL, article URL/headword, message;
- propose cleaned summary/description;
- show diff;
- apply only after explicit confirmation or narrow batch command.

## YouTrack cleanup direction after `/new`

Suggested next exploration:
1. Inventory current `eoru` unresolved/open issues by subsystem/type/state.
2. Find obvious cleanup batches:
   - old engine issues already fixed by backend revival (`eoru-1275`, `eoru-1276` already moved to `Verified` by Sasha);
   - Reformal boilerplate/reply issues;
   - `Исправлена` but not `Проверена` backlog;
   - stale duplicates/obsolete/won't-fix candidates.
3. Design helper scripts as read-only preview first, then apply only with confirmation.
4. Keep YouTrack primary; memory only points to issue IDs and recovery context.

## Recent prod dictionary update

2026-05-21 update completed to last Russian word `приёмчик`:
- pipeline: Dropbox sync-in → local import → sync-back → local DB dump → restore server DB → deploy `tekstoj`;
- import counts: Esperanto 46619, Russian 58766, EO search 93394, RU search 90348, fuzzy 838;
- dump kept at `/home/avo/rueo_master/tmp/rueo_db_20260520T214749Z.dump`;
- server restore completed normally (no `statistiko_pkey` duplicate failure this time);
- live checks passed: home 200, `/search?query=приёмчик` 200 with `count: 1`, `renovigxo.md` starts `21 мая 2026 года`.

Previous 2026-05-16 update was to `приёмная`; it had required manual recovery from `/home/avo/rueo_master/tmp/rueo_db_20260515T214441Z.dump` after `statistiko.id=1` duplicate failure.

Tracked by:
- `eoru-1419` (`statistiko` decommission)
- `eoru-1420` (restore hardening)

## Other prod notes

- `/search` dry-run rate limit is enabled and tracked in `eoru-1421`.
- Patron-list/frontend closeout is tracked in `eoru-1422`.
- Existing commits in `rueo_master`:
  - `08f5622 Extract patrons list`
  - `65d3031 Add PWA frontend deploy script`

## Repo status / caution

No commits were made.

Known uncommitted changes in `rueo_master`:
- `frontend-app/public/mecenatoj.txt`
- `memory-bank/active-context.md`
- `memory-bank/YOUTRACK_WORKFLOW.md`

Do not commit without Sasha’s confirmation. Do not run prod changes without explicit confirmation.

Cross-worktree caution:
- `rueo_master` is prod / Stage I, while `rueo_global` is the Stage II development tree.
- Be very careful with commits in `rueo_master`: before committing, check whether each change must also be ported to `rueo_global` to avoid Stage II regressions.
- Do not assume a `rueo_master`-only fix is complete unless it is deliberately prod-only; record or apply the corresponding `rueo_global` change before asking Sasha to approve a commit.
- Audit plan saved in `memory-bank/MASTER_GLOBAL_SYNC_AUDIT.md`.

## Latest YouTrack cleanup research — 2026-05-17

During the 2026-05-16/17 cleanup session, eoru-1424/eoru-1425 research advanced. Main notes and artifacts live outside the repo under `/home/avo/clawd/research/youtrack/`:

- `youtrack_reformal.py` + `youtrack-reformal-helper.md`: helper for Reformal-created issues (`list`, `preview`, gated `apply` with snapshots). It parses Reformal author/profile, `ia`, original subject/title, `rueo.ru/sercxo/<word>`, and message after `<br>`. Validated on saved pre-cleanup `eoru-1414` snapshot: proposed `двоюродный: орфографическая ошибка` and cleaned description 4130 → 411 chars.
- `eoru-reformal-html-inventory-2026-05-16.tsv`: inventory of 356 Reformal/HTML-like issues with extracted `subject`; use as an index, not as source of truth.
- Title-only cleanup applied in YouTrack for 18 exact Reformal-boilerplate tasks: `Реформал - новый комментарий к отзыву "..."` → `Комментарий к отзыву: ...`; no type/subsystem/state changes. Log: `reformal-title-only-apply-2026-05-16.json`.
- Thread fixture 1: `eoru-1380` root + `eoru-1381`–`eoru-1384` comments, all Won't fix, safe for future collapse testing.
- Thread fixture 2: Sasha identified `eoru-1373` as root for gerund forms; `eoru-1374` and `eoru-1375` linked to it via `Relates`. Log: `reformal-link-gerund-2026-05-16.json`.
- Manual Ctrl+Enter cleanup analysis: `eoru-manual-cleanup-analysis-2026-05-16.md/.tsv/.compact.txt`; 7 of 11 listed tasks are additions/proposals rather than typos. Future title classifier should treat `добавить`, `значение`, `перевод`, `пример`, `_инф._`, geo names as proposal/addition signals, not `орфографическая ошибка`.

Do not bulk-change old closed fields. Sasha allowed title-only changes, but state/type/subsystem should stay untouched unless explicitly requested.


## 2026-05-27 — prod dictionary update to `приехать`

Dictionary update completed on prod to last Russian word `приехать`.

Pipeline run:
- Dropbox sync-in → local import → sync-back → local DB dump → restore server DB → deploy `tekstoj`.
- Local import command: `./scripts/rueo_update.sh import-local --last-ru-letter 'приехать'`.
- Dump kept at: `/home/avo/rueo_master/tmp/rueo_db_20260526T222214Z.dump` (14M PostgreSQL custom dump).

Counts after import/local DB:
- Esperanto articles: 46625
- Russian articles: 58768
- EO search: 93405
- RU search: 90359
- fuzzy: 838

Prod verification:
- `https://rueo.ru/` HTTP 200.
- `/search?query=приехать` HTTP 200, `count: 1`, article shows редакция `2026-05-26`.
- `renovigxo.md` starts `27 мая 2026 года`.
- `klarigo.md` says Russian dictionary range `А — приехать` and EO stats `93405 слов в 46625 словарных статьях`.

Note: Sasha clarified that dictionary update workflow is allowed without extra prod confirmation; still keep normal safety checks and explicit confirmation for unrelated prod changes.

## 2026-06-06 — prod dictionary update to `призвание`

Dictionary update completed on prod to last Russian word `призвание`.

Pipeline run:
- Dropbox sync-in -> local import -> sync-back -> local DB dump -> restore server DB -> deploy `tekstoj`.
- Full command: `./scripts/rueo_update.sh run --last-ru-letter 'призвание'`.
- Dump kept at: `/home/avo/rueo_master/tmp/rueo_db_20260606T012424Z.dump` (14M PostgreSQL custom dump).

Counts after import/local DB:
- Esperanto articles: 46634
- Russian articles: 58755
- EO search: 93422
- RU search: 90357
- fuzzy: 838

Prod verification:
- `https://rueo.ru/` HTTP 200 via remote IP `72.56.13.203`.
- `/search?query=призвание` returned `count: 1`, article shows редакция `2026-06-05`.
- `renovigxo.md` starts `6 июня 2026 года`.
- `klarigo.md` says Russian dictionary range `А — призвание` and EO stats `93422 слова в 46634 словарных статьях`.

Commit/sync reminder from Sasha after this update:
- Keep `rueo_master` commits cautious because `rueo_global` contains Stage II development.
- Changes made in `rueo_master` should also land in `rueo_global` when applicable, so Stage II does not lose prod fixes/content updates.
- `frontend-app/public/mecenatoj.txt` was ported to `rueo_global`; broader code audit is planned in `memory-bank/MASTER_GLOBAL_SYNC_AUDIT.md`.
