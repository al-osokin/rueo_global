# Active Context — rueo.ru / YouTrack cleanup

Updated: 2026-06-27 19:35 (Europe/Moscow)

## 2026-06-27 — rueo.ru `/orph` mail route and Date header hotfix

Production `rueo.ru` on FirstVDS Stage had two mail issues in the backend `/orph` feedback path.

Delivery fix:
- Sasha's test `/orph` message did not arrive.
- Diagnosis on server: `rueo-backend-1` sends via `smtplib` to host Exim at `SMTP_HOST=172.18.0.1`, `SMTP_PORT=587`, with empty SMTP auth and `SMTP_FROM/SMTP_TO=vortaristo@a-v-o.ru`.
- Exim saw the backend as unauthenticated Docker client `172.18.0.2` and rejected sender domain `a-v-o.ru` at RCPT with `Unauthorized access`.
- Server backup: `/root/exim-hardening-backups/20260627-1914-rueo-docker-relay/`.
- Added the private `rueo_default` Docker subnet `172.18.0.0/16` to `/etc/exim4/relay_from_hosts` and reloaded Exim.
- Verified direct SMTP from `rueo-backend-1`: message `1wdVgH-0005Zu-0X` accepted and delivered to `vortaristo@a-v-o.ru`.
- Verified real `/orph`: message `1wdVga-0005cL-2x` accepted and delivered via `R=procmail T=dovecot_deliver_pipe`.

Date header fix:
- The backend-generated message had no `Date:` header; The Bat! displayed it as `30 Dec 1899 03:00`.
- Local source fix in `backend/app/main.py`: import `formatdate` and `make_msgid`; add `Date` and `Message-ID` headers before `set_content()`.
- Hotfixed running container by copying the updated `main.py` into `rueo-backend-1`; backup: `/root/rueo-backend-hotfix-backups/20260627-1933-mail-date-messageid/`.
- Restarted `rueo-backend-1`; `python -m py_compile /app/app/main.py` passed.
- Test `/orph` after hotfix delivered Exim id `1wdVya-0006h8-1L`; stored message contains:
  - `Date: Sat, 27 Jun 2026 16:33:51 +0000`
  - `Message-ID: <178257803195.1.18446384458891057777@rueo.ru>`
- Committed the patched running container back to local Docker image `alosokin/rueo-backend:latest` so a local container recreation uses the fix. Image changed from `sha256:52933138...` to `sha256:1ade7723...`.
- Checked `exim4`, `dovecot`, `docker` active and `rueo-backend-1` up.

Git state:
- Sasha confirmed the fixed message arrives with a normal date in The Bat! and explicitly approved making a commit.
- Commit should include `backend/app/main.py` and `memory-bank/active-context.md`.

## 2026-06-09 — legacy Rueo names on emergency channel

Sasha reported that some users still reach the dictionary through `eoru.ru`, and some use `old.rueo.ru`.

Configured on `stage-test` (`37.46.132.178`) through the existing emergency tunnel:
- New nginx config: `/etc/nginx/conf.d/rueo-extra-tunnel-proxy.conf`.
- `old.rueo.ru` / `www.old.rueo.ru` HTTP redirects to HTTPS; HTTPS proxies through `https://127.0.0.1:18443` with `proxy_ssl_name old.rueo.ru`.
- Copied origin certificate to `/var/www/httpd-cert/tunnel-proxy/rueo-extra/old.rueo.ru_le2.{crtca,key}`; cert is valid until `2026-08-06`. It covers only `old.rueo.ru`, not `www.old.rueo.ru`, matching the origin certificate state.
- `eoru.ru` / `www.eoru.ru` HTTP and HTTPS redirect to `https://rueo.ru$request_uri`; ACME webroot prepared at `/var/www/acme-eoru/.well-known/acme-challenge/`.
- `eoru.ru` had no valid HTTPS cert on origin: current origin HTTPS presents the default `a-v-o.ru` certificate. Attempted Let's Encrypt HTTP-01 issue on origin failed because LE could not fetch validation data from `72.56.13.203`, consistent with the Timeweb path incident.
- After Sasha moved DNS toward `37.46.132.178`, issued a new stage-test Let's Encrypt ECDSA cert for `eoru.ru` + `www.eoru.ru`, installed at `/var/www/httpd-cert/tunnel-proxy/rueo-extra/eoru.ru.{crtca,key}`; valid until `2026-09-07`.

Verification with forced resolve to `37.46.132.178`:
- `http://eoru.ru/` -> `301 https://rueo.ru/`.
- `http://www.eoru.ru/test?q=1` -> `301 https://rueo.ru/test?q=1`.
- `https://eoru.ru/test?q=1` -> `301 https://rueo.ru/test?q=1`.
- `https://www.eoru.ru/` -> `301 https://rueo.ru/`.
- `http://old.rueo.ru/` -> `301 https://old.rueo.ru/`.
- `https://old.rueo.ru/` -> `200` through the tunnel.

DNS transition at 2026-06-09 15:32 MSK: `1.1.1.1` and `9.9.9.9` already saw `eoru.ru -> 37.46.132.178`; Google `8.8.8.8` still briefly returned old `72.56.13.203` for apex. `old.rueo.ru` was already updated on checked public resolvers; `www` names are CNAMEs and should follow.

## 2026-06-08 — PWA news refresh cache fix deployed

Sasha reported that an updated root `news.md` on prod did not appear in the PWA after manual refresh, forced reload, or browser cache clearing.

Findings:
- Live `https://rueo.ru/news.md` was already fresh on the server (`Last-Modified: 2026-06-08 00:22:48 GMT`, size 8761), so the stale display was frontend/PWA-cache behavior, not a missing upload.
- `NewsFeed.vue` fetched `/news.md` without cache-busting/no-cache headers.
- Auto-update only treated a changed number of news blocks as an update; edits inside existing blocks were ignored.
- `.htaccess` disabled cache only for `service-worker.js`, but the Quasar PWA build outputs and deploy script use `sw.js`.

Local fix applied in both `rueo_master` and `rueo_global`:
- `NewsFeed.vue`: fetch `/news.md?ts=...` with `cache: 'no-store'`, store the raw source text, and update when text changes.
- `custom-service-worker.js`: exclude `news.md` from precache and serve `/news.md` network-only.
- `public/.htaccess`: no-cache headers for both `sw.js`/`service-worker.js` and `news.md`.
- frontend version bumped locally to `1.0.7` in both trees so deployed PWA clients can detect the code update via `/package.json`.

Verification before deploy:
- `npm --prefix frontend-app run build -- -m pwa` passed in `rueo_master`.
- Same build passed in `rueo_global`.

Prod deploy:
- Sasha approved deploy on 2026-06-08 around 03:50 MSK.
- `scripts/deploy_frontend_pwa.sh --apply` initially built `1.0.7` but stopped before rsync because public `rueo.ru` now points to emergency proxy and SSH host key differs.
- Re-ran deploy against origin explicitly: `SERVER_SSH=root@72.56.13.203 ./scripts/deploy_frontend_pwa.sh --apply --skip-build`.
- Deployed package verification printed `1.0.7`.
- Live checks through public `https://rueo.ru/` and direct origin `--resolve rueo.ru:443:72.56.13.203`:
  - `/package.json` returns `1.0.7`;
  - `/sw.js` contains `v1.0.7` and the `/news.md` handling;
  - `/package.json`, `/sw.js`, and `/news.md` all return `Cache-Control: no-cache, no-store, must-revalidate`, `Pragma: no-cache`, `Expires: 0`.

Server-side note:
- `.htaccess` was fixed in the repo, but live origin is Nginx and did not apply those headers.
- Added matching live Nginx locations in `/etc/nginx/vhosts/slovari/rueo.ru.conf` for `/package.json`, `/news.md`, and `~ ^/(sw|service-worker)\.js$`; `nginx -t` passed and Nginx was reloaded.
- Backup on origin: `/etc/nginx/vhosts/slovari/rueo.ru.conf.bak-20260608-035303-pwa-cache`.

No commit has been made yet. Per Sasha's rule, wait for local review/confirmation before committing; if committing, include these code/version changes in both worktrees and this handoff note.

Follow-up local fix on 2026-06-08:
- Sasha noticed that the first `#` heading in a `news.md` block rendered smaller than later `#` headings: DOM showed `ПЕРЕПИСКА` as `div.text-h6`, while `ВАЖНЫЕ НОВОСТИ` stayed a Markdown `<h1>`.
- Root cause: `NewsFeed.vue` extracts the first `# ...` heading from each `---` block into `item.title`, removes it from Markdown content, then renders it as Quasar `div.text-h6`.
- Local fix applied in both `rueo_master` and `rueo_global`: render extracted news titles as semantic `<h1 class="news-card-title">` with the same size as Markdown `h1`; only keep tighter zero top margin for card layout.
- Frontend version bumped locally to `1.0.8` in both trees (`package.json`, `package-lock.json`, `public/package.json`) so a later PWA deploy signals an app update.
- Verification: `npm --prefix frontend-app run build -- -m pwa` passed in both `rueo_master` and `rueo_global`.

News structure follow-up on 2026-06-08:
- Sasha restructured the local shared `news.md` to use `#` headings as top-level sections (`ПЕРЕПИСКА`, `ВАЖНЫЕ НОВОСТИ`, `НАША ПОЧТИ БЕГУЩАЯ СТРОКА`) and `##` headings as individual news items. `---` separators were removed from the file and are no longer needed.
- `frontend-app/public/news.md` is an absolute symlink to `/home/avo/.rueo-shared/news.md` and is explicitly ignored by `.gitignore`, while `/home/avo/.rueo-shared` is not a Git repository. Therefore Sasha's content edit cannot be pushed by the code commit and must be deployed/synced through the shared-news path separately.
- `NewsFeed.vue` parser was changed from `---` blocks to a two-level model: `#` sections + `##` news items. Pagination and homepage limits count only `##` items; section intro text such as `ПЕРЕПИСКА` is shown outside the item count.
- Rendering now groups visible news items back under their section headings, so `#` headings are shown once per visible section and `##` headings are not duplicated.
- Homepage limit remains 5 news items; `/novajxoj` still paginates 10/20/50 items.
- Verification after parser change: `npm --prefix frontend-app run build -- -m pwa` passed in both `rueo_master` and `rueo_global`.
- Prod deploy completed on 2026-06-08 04:43 MSK:
  - Deployed from `rueo_master` to origin explicitly with `SERVER_SSH=root@72.56.13.203 ./scripts/deploy_frontend_pwa.sh --apply`.
  - First deploy showed live `/package.json` as `1.0.8`, but the built `/sw.js` still used `CACHE_VERSION = 'v1.0.7'` because `frontend-app/src-pwa/custom-service-worker.js` has a separate manual constant.
  - Fixed `CACHE_VERSION` to `v1.0.8` in both `rueo_master` and `rueo_global`, rebuilt, and redeployed.
  - Live verification through public `https://rueo.ru/` and direct origin `--resolve rueo.ru:443:72.56.13.203`: `/package.json` returns `1.0.8`; `/sw.js` contains `c="v1.0.8"` and network-only `/news.md`; `/sw.js` still has no-cache headers.
  - `npm --prefix frontend-app run build -- -m pwa` passed in `rueo_global` after the service-worker constant fix.
- Not committed after this deploy. Current expected local changes: `frontend-app/src-pwa/custom-service-worker.js` in both worktrees and this `memory-bank/active-context.md`; `rueo_global` also has pre-existing unrelated dirty files (`AdminV4Review.vue`, `.learnings/`, `backend/.env.lmstudio`).
- Deployment defaults follow-up on 2026-06-08:
  - While the Timeweb network path is unreliable and public `rueo.ru` lives behind the emergency proxy, `scripts/deploy_frontend_pwa.sh` and `scripts/rueo_update.sh` now default to `SERVER_SSH=root@72.56.13.203` in both `rueo_master` and `rueo_global`.
  - Added `memory-bank/FRONTEND_DEPLOYMENT.md` in both worktrees with the current deploy channel and PWA version-bump rules.
  - Important version rule: use `frontend-app/bump-version.sh <version>`; the version is not only in `package.json`, it must also be synchronized to `package-lock.json`, `public/package.json`, and `src-pwa/custom-service-worker.js` (`CACHE_VERSION`).

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

## 2026-06-10 — prod dictionary update to `призёр`

Dictionary update completed on prod to last Russian word `призёр`.

Pipeline run:
- Dropbox sync-in -> local import -> sync-back -> local DB dump -> restore server DB -> deploy `tekstoj`.
- Full command: `./scripts/rueo_update.sh run --last-ru-letter 'призёр'`.
- Dump kept at: `/home/avo/rueo_master/tmp/rueo_db_20260610T133357Z.dump` (14M PostgreSQL custom dump).

Counts after import/local DB:
- Esperanto articles: 46642
- Russian articles: 58757
- EO search: 93435
- RU search: 90363
- fuzzy: 838

Prod verification:
- `https://rueo.ru/` HTTP 200.
- `/search?query=призёр` returned `count: 1`, article shows редакция `2026-06-09`.
- `renovigxo.md` starts `10 июня 2026 года`.
- `klarigo.md` says Russian dictionary range `А — призёр` and EO stats `93435 слов в 46642 словарных статьях`.

## 2026-06-10 — old.rueo.ru legacy updater copied locally for study

Sasha asked about reviving updates for old.rueo.ru. Existing manual workflow: copy dictionary sources to the server, open the updater UI on port `12443`, run the old Python/Tornado updater there.

Server source inspected at `/var/www/slovari/data/www/updater.rueo.ru` on origin `72.56.13.203`:
- Live service: `vortaro_updater.service`, process `env311/bin/python updater_src/web.py -c vu.yml`, user `slovari`.
- Port `12443` listens on `0.0.0.0` and `::`.
- Main code is under `updater_src/`; top-level `src/` contains server-side dictionary source snapshot and `last-ru-letter.txt`.
- `vu.yml` contains production DB/UI credentials; treat the local copy as sensitive and do not commit it.
- Server `src/last-ru-letter.txt` currently says `президентша`, so the old contour is behind the new prod update pipeline.
- The old updater is a Tornado web UI that calls PHP importer `vortaro_updater.php` or `vortaro_updater_8.php`, first against test MySQL DB, then backs up production MySQL with `mysqldump`, imports production DB, updates `old.rueo.ru/tekstoj/klarigo.textile` and prepends date to `renovigxo.textile`; rollback uses `mysql < backup`.

Local action:
- Existing local `/home/avo/updater.rueo.ru` was preserved as `/home/avo/updater.rueo.ru.backup-20260610-195936`.
- Fresh server copy was rsynced to `/home/avo/updater.rueo.ru`, excluding top-level `env/`, `env311/`, and `__pycache__/`.
- Copied payload includes `updater_src/` with its Git history, `src/`, `vu.yml`, `vu.log`, `index.html`, and helper files.

Likely direction:
- Short-term diagnostic bridge can proxy `12443` through stage-test, but only with tight access controls.
- Better durable path: add an old.rueo.ru legacy MySQL build/restore step to the same dictionary update pipeline, using this copied updater code as reference and avoiding the browser UI.

Follow-up implementation started the same evening:
- `scripts/rueo_update.sh` now has a separate old.rueo.ru contour; the existing `run` command is intentionally unchanged.
- New commands:
  - `sync-old-src --last-ru-letter <word>`: rsync current `backend/data/src/{VortaroRE-daily,VortaroER-daily}` to `${OLD_UPDATER_DIR}/src` on `${OLD_UPDATER_SSH}` and writes `last-ru-letter.txt` in CP1251.
  - `update-old-db --last-ru-letter <word>`: over SSH, runs the legacy PHP 8 importer first on `slovari_vortaro_test`, then backs up `slovari_vortaro` with `mysqldump`, imports production MySQL, and regenerates old `klarigo.textile` / `renovigxo.textile` from the prod import log.
  - `run-old --last-ru-letter <word>`: sync + old DB update.
  - `run-all --last-ru-letter <word>`: existing new-site full pipeline, then `run-old`.
- Defaults point to origin `root@72.56.13.203`, updater dir `/var/www/slovari/data/www/updater.rueo.ru`, DBs `slovari_vortaro` and `slovari_vortaro_test`.
- Verification so far: `bash -n scripts/rueo_update.sh` passes; help output shows the new commands; read-only remote prerequisite check passed (`/usr/bin/php` is PHP 8.2, `env311/bin/python` can read `vu.yml`, config paths match).
- Not yet run against old production DB from this new CLI path. Sasha is doing the immediate manual update through `72.56.13.203:12443`; use that result as a comparison before trusting the new command for routine updates.
- The new CLI path does not need the always-on Python/Tornado web UI on port `12443`. It only needs the updater directory, `src/`, `vu.yml`, `/usr/bin/php`, MySQL tools, and `env311/bin/python` as a command-line interpreter for small YAML/text-generation helpers. It is therefore OK to stop/disable `vortaro_updater.service` when the browser UI is no longer needed.

Local old.rueo.ru development path added and tested:
- `scripts/rueo_update.sh update-old-local-db --last-ru-letter <word>` imports current `backend/data/src` into local MySQL `slovari_vortaro` without SSH/production access, then regenerates local `/home/avo/old.rueo.ru/tekstoj/klarigo.textile` and `renovigxo.textile`.
- Local DB connection is controlled by env vars: `OLD_LOCAL_DB_HOST`, `OLD_LOCAL_DB`, `OLD_LOCAL_DB_USER`, `OLD_LOCAL_DB_PASSWORD`. Sasha updated `/home/avo/old.rueo.ru/index.php` to use local credentials; do not write those credentials into the repo or handoff.
- `/home/avo/updater.rueo.ru/updater_src/vortaro_updater_8.php` was locally patched to accept `OLD_RUEO_MYSQL_HOST`, `OLD_RUEO_MYSQL_USER`, and `OLD_RUEO_MYSQL_PASSWORD`, so the script does not need hardcoded local credentials.
- First local run with the active credentials from `index.php` completed on 2026-06-10:
  `./scripts/rueo_update.sh update-old-local-db --last-ru-letter 'призёр'`
  with log `/home/avo/rueo_master/tmp/old_rueo_local_import_20260610T173133Z.log`.
- Local legacy counts after import: `artikoloj` 46642, `artikoloj_ru` 58757, `sercxo` 93454, `sercxo_ru` 90365, `neklaraj` 838.
- MySQL check found `призёр` in `sercxo_ru`, linked to article `32170`; article text begins `[призёр] (_лицо, получившее приз_) premiito; ...`.
- Local `klarigo.textile` now says range `А -- призёр`, EO `93454 слова в 46642 словарных статьях`; `renovigxo.textile` starts `10 июня 2026 года`.
- Important legacy preservation rule: `statistiko` is a live old-site usage/search statistics table and must not be overwritten by any future MySQL dump/restore flow. The legacy PHP importer is safe here: it truncates only `artikoloj`, `artikoloj_ru`, `sercxo`, `sercxo_ru`, and `neklaraj`; it does not touch `statistiko`. If a local MySQL dump is later deployed to origin/stage instead of running the PHP importer in place, dump/restore only those five dictionary tables (plus explicitly intended helper tables), or preserve and restore `statistiko` around the import.
- Sasha stopped `vortaro_updater.service`; the CLI path does not require the web UI. Verified afterward: service is `inactive` and port `12443` is not listening.
- First production CLI attempt exposed two fixups:
  - the remote `updater_src/vortaro_updater_8.php` did not yet support `OLD_RUEO_MYSQL_*`, so it was backed up as `updater_src/vortaro_updater_8.php.bak-20260610T174536Z` and replaced with the local env-aware version;
  - the server-side log parser was updated to understand both bracket stats and the PHP 8 daily log format (`Processing language`, `Dictionary entries processed`, `Words processed`).
- Final production old.rueo.ru CLI update completed on origin with:
  `./scripts/rueo_update.sh update-old-db --last-ru-letter 'призёр'`.
  Backup: `/root/old_rueo_vortaro_20260610T174718Z.sql` (52M).
  Logs: `/var/www/slovari/data/www/updater.rueo.ru/logs/old-rueo-test-20260610T174718Z.log` and `old-rueo-prod-20260610T174718Z.log`.
- Origin MySQL verification after final run: `artikoloj` 46642, `artikoloj_ru` 58757, `sercxo` 93454, `sercxo_ru` 90365, `neklaraj` 838, `statistiko` 263252, and `sercxo_ru` has one `призёр` entry linked to article `32170`.
- Origin old-site texts now say range `А -- призёр`; `renovigxo.textile` starts `10 июня 2026 года`.
- HTTP verification passed for forced origin and proxy routes:
  `https://old.rueo.ru/sercxo/призёр` returned content containing both `призёр` and `premiito` via `72.56.13.203` and via `37.46.132.178`.

## 2026-06-16 — prod dictionary update to `призмообразный`

Dictionary update completed on prod to last Russian word `призмообразный`, including the new old.rueo.ru legacy contour.

Pipeline run:
- New rueo.ru command: `./scripts/rueo_update.sh run --last-ru-letter 'призмообразный'`.
- Old rueo.ru command after successful new-site run: `./scripts/rueo_update.sh run-old --last-ru-letter 'призмообразный'`.
- New-site PostgreSQL dump kept at: `/home/avo/rueo_master/tmp/rueo_db_20260615T212352Z.dump`.

Counts after new-site import/local DB:
- Esperanto articles: 46643
- Russian articles: 58756
- EO search: 93439
- RU search: 90377
- fuzzy: 838

Tracking summary:
- EO: `articles_changed` 5, `articles_auto_dated` 2, `articles_new` 3.
- RU: `articles_changed` 23, `articles_auto_dated` 21, `articles_new` 6.

New prod verification:
- `https://rueo.ru/search?query=призмообразный` returned HTTP 200 with `count: 1`.
- `renovigxo.md` starts `16 июня 2026 года`.

old.rueo.ru legacy update:
- Backup: `/root/old_rueo_vortaro_20260615T212418Z.sql`.
- Test log: `/var/www/slovari/data/www/updater.rueo.ru/logs/old-rueo-test-20260615T212418Z.log`.
- Prod log: `/var/www/slovari/data/www/updater.rueo.ru/logs/old-rueo-prod-20260615T212418Z.log`.
- Origin MySQL table counts after run: `artikoloj` 46643, `artikoloj_ru` 58756, `sercxo` 93458, `sercxo_ru` 90379, `neklaraj` 838, `statistiko` 264644.
- `statistiko` was not truncated by the importer and remains populated.
- HTTP verification passed: `https://old.rueo.ru/sercxo/призмообразный` returned HTTP 200 with a dictionary article, permanent link, and revision marker.
- Caveat: a manually constructed CP1251-percent URL for the same word triggered old `sercxo.php` memory exhaustion; normal UTF-8 URL verification passed.
