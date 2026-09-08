# Active Context — rueo.ru / YouTrack cleanup

Updated: 2026-09-08 03:08 (Europe/Moscow)

## 2026-09-08 — branch realignment and friendly projects

- Audited the Stage I repository after cherry-picks had made `master` and
  `develop` histories difficult to reconcile. The deployed 1.0.8 code and the
  current production workflow are based on `develop`; the old `master` was
  still at 1.0.5.
- Preserved the old remote `master` exactly as
  `archive/master-before-realign-2026-09-08` at
  `2a6da318b913b9f44b8545bab352f1219b860dd0`.
- Pushed the four local production commits on `develop`, then realigned remote
  `master` to the exact `develop` tip with `--force-with-lease`. Remote
  `master`, remote `develop`, and both local branches were verified at
  `eb646a43725bf4ebd85cf559673c092584e6bcd6`. `master` remains the GitHub
  default branch. The obsolete local `rueo_master` branch had no unique work
  and was removed after ancestry checks.
- Added the accepted `Проекты` navigation destination and `/projektoj` page to
  the current Stage I `develop` base. The page lists Biologio and Frazaro with
  separate Russian and Esperanto descriptions. Desktop, mobile, light, and
  dark layouts were reviewed; targeted ESLint, strict OpenSpec validation, and
  the Quasar PWA build passed.
- Committed the Stage I page as `698d576`; remote `develop` and `master` were
  both advanced to it normally. Mirrored it to Stage II as `ac506e2` without
  touching its unrelated working-tree changes.
- Removed the temporary `/home/avo/rueo_menu_master` worktree and its local
  `feature/friendly-projects-page` branch after confirming that all feature
  files were already preserved in Stage I. The old baseline remains recoverable
  from the remote archive branch.
- After Sasha updated the shared `news.md`, bumped both Stage I and Stage II to
  PWA version `1.1.0` (`941f064` and `939fb67`). Both Quasar PWA builds passed;
  the Stage I build contained the exact source news hash
  `694579b406955de7e00d53743371ec531d2e45c9394fae9acbda97ea978d9b0f`,
  the matching service-worker cache version, and `manifest-1.1.0.json`.
- Deployed the Stage I PWA to `firstvds-stage` with the standard frontend
  deploy script after a clean dry run. External HTTP verification returned
  version `1.1.0`, the exact news hash above, HTTP 200 for `/projektoj`, and the
  same application shell as `/`. Protected `backend`, `webstat`, and `cgi-bin`
  directories remained present. No database operation was performed.

## 2026-09-06 — prod dictionary refresh to `прилечь`

- Completed the full new + legacy production pipeline with
  `./scripts/rueo_update.sh run-all --last-ru-letter 'прилечь'` through
  native worker `/root/rueo_update_prilech`, exec session `37794`, PID
  `536018`. Worker log:
  `/home/avo/rueo_master/tmp/rueo_update_20260905T214254Z.log`.
- Database safety: both production databases on `firstvds-stage` were
  classified as persistent. Before mutation, protected counts were recorded
  and fresh verified snapshots were created:
  `/root/rueo_db_preupdate_20260905T214254Z.dump` (14,936,134 bytes,
  SHA-256
  `5299adf75ab0b8e7478807e6cece29a6b32df574f9c8b163d72d17bd48fab9c6`)
  and `/root/old_rueo_vortaro_preupdate_20260905T214254Z.sql` (56,166,058
  bytes, SHA-256
  `92b9d90686c047b14a70f7b1392ed4ee591b617f968a8fe74c053510327f8be3`).
  PostgreSQL passed `pg_restore -l`; the MySQL dump has its completion marker
  and includes `statistiko`.
- New PostgreSQL dump:
  `/home/avo/rueo_master/tmp/rueo_db_20260905T214550Z.dump` (14,772,764
  bytes, SHA-256
  `bfba8aa11031f2b8adecf14aeec4340b49c8800ce0f54502354abab9e37941cd`,
  `pg_restore -l` passed).
- Legacy backup: `/root/old_rueo_vortaro_20260905T214624Z.sql` (56,166,058
  bytes, SHA-256
  `e6688f51d654f6bf0f4e0cb552d364a166acf6677de5e5e10f4c93da733b7d19`).
  Test/prod logs are
  `/var/www/slovari/data/www/updater.rueo.ru/logs/old-rueo-test-20260905T214624Z.log`
  and
  `/var/www/slovari/data/www/updater.rueo.ru/logs/old-rueo-prod-20260905T214624Z.log`.
- Counts before: PostgreSQL `artikoloj=46686`, `artikoloj_ru=58582`,
  `sercxo=93574`, `sercxo_ru=90279`, `neklaraj=838`; MySQL
  `artikoloj=46686`, `artikoloj_ru=58582`, `sercxo=93594`,
  `sercxo_ru=90281`, `neklaraj=838`, `statistiko=286710`.
- Counts after: PostgreSQL `artikoloj=46691`, `artikoloj_ru=58568`,
  `sercxo=93603`, `sercxo_ru=90278`, `neklaraj=838`; MySQL
  `artikoloj=46691`, `artikoloj_ru=58568`, `sercxo=93623`,
  `sercxo_ru=90280`, `neklaraj=838`, `statistiko=286711`. The 14-article
  Russian reduction and one-entry Russian search reduction are identical in
  both independent importers and match the current source output; Esperanto
  and Esperanto search counts increased, fuzzy stayed stable, and live
  `statistiko` was preserved (the one-row increase came from the supervisor's
  legacy HTTP verification).
- Sasha's ready-range metrics in deployed `klarigo.md`: `32287` ready
  Russian–Esperanto articles and `52804` words, range `А — прилечь`. These
  increased from `32263` / `52761` and remain separate from total technical
  table counts.
- `https://rueo.ru/search?query=прилечь`: HTTP 200, `count=1`, article
  present. `https://old.rueo.ru/sercxo/прилечь`: HTTP 200, article present.
  Both `renovigxo` files start with `6 сентября 2026 года`.
- Durable state `/home/avo/rueo_master/tmp/rueo_update_active.json` is
  `completed`. No commit, cron/Gateway change, frontend deploy, or unrelated
  mutation was performed.

## 2026-08-27 — prod dictionary refresh to `прикупить`

- Completed the full new + legacy production pipeline with
  `./scripts/rueo_update.sh run-all --last-ru-letter 'прикупить'` through
  native worker `/root/rueo_update_prikupit` and recoverable background PID
  `1550269`. Worker log:
  `/home/avo/rueo_master/tmp/rueo_update_20260826T211334Z.log`.
- Database safety: both production databases on `firstvds-stage` were
  classified as persistent. Before mutation, protected counts were recorded
  and fresh verified snapshots were created:
  `/root/rueo_db_preupdate_20260826T211303Z.dump` (14,896,145 bytes,
  SHA-256
  `ca85d31a37587ef7bccbda9d468202f716009781d0fac157cd3cd9a04090119c`)
  and `/root/old_rueo_vortaro_preupdate_20260826T211303Z.sql` (55,909,073
  bytes, SHA-256
  `1fe5ee833760e151139ca73e2f2d8c70baec22923544c5c1c1dfccada427a7ed`).
  PostgreSQL passed `pg_restore -l`; the MySQL dump has its completion marker
  and includes `statistiko`.
- New PostgreSQL dump:
  `/home/avo/rueo_master/tmp/rueo_db_20260826T211559Z.dump` (14,741,846
  bytes, SHA-256
  `92bb0ba73fc68b4a12ecc51021ded7b349bf129fe684821a8e12894a17fa9e5b`,
  `pg_restore -l` passed).
- Legacy backup: `/root/old_rueo_vortaro_20260826T211636Z.sql` (55,909,073
  bytes, SHA-256
  `72e9d34f5d9f14b24b70cb9cb2cd650a1b6f2b45146d20c4badf99c4ae248ccc`).
  Test/prod logs are
  `/var/www/slovari/data/www/updater.rueo.ru/logs/old-rueo-test-20260826T211636Z.log`
  and
  `/var/www/slovari/data/www/updater.rueo.ru/logs/old-rueo-prod-20260826T211636Z.log`.
- Counts before: PostgreSQL `artikoloj=46674`, `artikoloj_ru=58586`,
  `sercxo=93548`, `sercxo_ru=90268`, `neklaraj=838`; MySQL
  `artikoloj=46674`, `artikoloj_ru=58586`, `sercxo=93568`,
  `sercxo_ru=90270`, `neklaraj=838`, `statistiko=283555`.
- Counts after: PostgreSQL `artikoloj=46686`, `artikoloj_ru=58582`,
  `sercxo=93574`, `sercxo_ru=90279`, `neklaraj=838`; MySQL
  `artikoloj=46686`, `artikoloj_ru=58582`, `sercxo=93594`,
  `sercxo_ru=90281`, `neklaraj=838`, `statistiko=283557`. The four-article
  Russian reduction is identical in both independent importers and matches
  the current source output; Esperanto and search counts increased, fuzzy
  stayed stable, and live `statistiko` was preserved (the two-row increase
  came from worker and supervisor legacy HTTP verification).
- Sasha's ready-range metrics in deployed `klarigo.md`: `32263` ready
  Russian–Esperanto articles and `52761` words, range `А — прикупить`.
  These increased from `32256` / `52749` and remain separate from total
  technical table counts.
- `https://rueo.ru/search?query=прикупить`: HTTP 200, `count=1`, article
  present. `https://old.rueo.ru/sercxo/прикупить`: HTTP 200, article present.
  Both `renovigxo` files start with `27 августа 2026 года`.
- Durable state `/home/avo/rueo_master/tmp/rueo_update_active.json` and global
  task state `/home/avo/clawd/.active-task.json` are `completed`. No commit,
  cron/Gateway change, frontend deploy, or unrelated mutation was performed.

## 2026-08-19 — prod dictionary refresh to `прикроватный`

- Completed the full new + legacy production pipeline with
  `./scripts/rueo_update.sh run-all --last-ru-letter 'прикроватный'` through
  durable exec session `23731` (PID `3244115`). Worker log:
  `/home/avo/rueo_master/tmp/rueo_update_20260818T211711Z.log`.
- Database safety: both production databases on `firstvds-stage` were
  classified as persistent. Before mutation, protected counts were recorded
  and fresh verified snapshots were created:
  `/root/rueo_db_preupdate_20260818T211711Z.dump` (14,859,991 bytes,
  SHA-256
  `23d9566417b16fe2792f81a70854f083a74c259bfed7707f1e190bcae0cca2e1`)
  and `/root/old_rueo_vortaro_preupdate_20260818T211711Z.sql` (55,828,601
  bytes, SHA-256
  `6d4b93b2e8ac22bd292e35ed65e38ee5c9da0d04326f10a8972392abfc9b5d27`).
  PostgreSQL passed `pg_restore -l`; the MySQL dump has its completion marker
  and includes `statistiko`.
- New PostgreSQL dump:
  `/home/avo/rueo_master/tmp/rueo_db_20260818T212019Z.dump` (14,749,199
  bytes, SHA-256
  `7c1951250f121f0c3175885f2bce70d4bfa187eda67520369342e045ed53d1d7`,
  `pg_restore -l` passed).
- Legacy backup: `/root/old_rueo_vortaro_20260818T212055Z.sql` (55,828,543
  bytes, SHA-256
  `d49fa6a49b45b22aaac96fe5e3e2ae4d4c56fcf33251b33d4282a92d9a4e5399`).
  Test/prod logs are
  `/var/www/slovari/data/www/updater.rueo.ru/logs/old-rueo-test-20260818T212055Z.log`
  and
  `/var/www/slovari/data/www/updater.rueo.ru/logs/old-rueo-prod-20260818T212055Z.log`.
- Counts before: PostgreSQL `artikoloj=46669`, `artikoloj_ru=58628`,
  `sercxo=93533`, `sercxo_ru=90303`, `neklaraj=838`; MySQL
  `artikoloj=46669`, `artikoloj_ru=58628`, `sercxo=93553`,
  `sercxo_ru=90305`, `neklaraj=838`, `statistiko=282578`.
- Counts after: PostgreSQL `artikoloj=46674`, `artikoloj_ru=58586`,
  `sercxo=93548`, `sercxo_ru=90268`, `neklaraj=838`; MySQL
  `artikoloj=46674`, `artikoloj_ru=58586`, `sercxo=93568`,
  `sercxo_ru=90270`, `neklaraj=838`, `statistiko=282580`. The Russian
  article/search reductions are identical in both independent importers and
  match the current source output; Esperanto counts increased, fuzzy stayed
  stable, and live `statistiko` was preserved (the two-row increase came from
  legacy HTTP verification requests).
- Sasha's ready-range metrics in deployed `klarigo.md`: `32256` ready
  Russian–Esperanto articles and `52749` words, range `А — прикроватный`.
  These increased from `32247` / `52728` and remain separate from total
  technical table counts.
- `https://rueo.ru/search?query=прикроватный`: HTTP 200, `count=1`, article
  present. `https://old.rueo.ru/sercxo/прикроватный`: HTTP 200, article
  present. Both `renovigxo` files start with `19 августа 2026 года`.
- Durable state `/home/avo/rueo_master/tmp/rueo_update_active.json` is
  `completed`. No commit, cron/Gateway change, frontend deploy, or unrelated
  mutation was performed.

## 2026-08-11 — prod dictionary refresh to `прикраса`

- Completed the full new + legacy production pipeline with
  `./scripts/rueo_update.sh run-all --last-ru-letter 'прикраса'` through
  durable exec session `14165` (PID `512730`). Worker log:
  `/home/avo/rueo_master/tmp/rueo_update_20260810T212740Z.log`.
- Database safety: both production databases on `firstvds-stage` were
  classified as persistent. Before mutation, protected counts were recorded
  and fresh verified snapshots were created:
  `/root/rueo_db_preupdate_20260810T212740Z.dump` (14,780,861 bytes,
  SHA-256
  `a45a9b01639057bbb70feacde478f0444a1fd5bf8ba362eb229d5bd0347ccb63`)
  and `/root/old_rueo_vortaro_preupdate_20260810T212740Z.sql` (55,798,918
  bytes, SHA-256
  `116f6899243ac0cb4584880490913415d1ab399140e4f84507dbd42a09f36a2a`).
  PostgreSQL passed `pg_restore -l`; the MySQL dump has its completion marker
  and includes `statistiko`.
- New PostgreSQL dump:
  `/home/avo/rueo_master/tmp/rueo_db_20260810T213043Z.dump` (14,719,836
  bytes, SHA-256
  `2cb0abad1164da360d134dbd1652e7055d664feeec57250d12682e216b46f1f8`,
  `pg_restore -l` passed).
- Legacy backup: `/root/old_rueo_vortaro_20260810T213124Z.sql` (55,798,918
  bytes, SHA-256
  `1f1ea092f7de51cd7d38311097fd59459ad650fe7b577b05bff6f1359bd8f0db`).
  Test/prod logs are
  `/var/www/slovari/data/www/updater.rueo.ru/logs/old-rueo-test-20260810T213124Z.log`
  and
  `/var/www/slovari/data/www/updater.rueo.ru/logs/old-rueo-prod-20260810T213124Z.log`.
- Counts before: PostgreSQL `artikoloj=46669`, `artikoloj_ru=58634`,
  `sercxo=93532`, `sercxo_ru=90296`, `neklaraj=838`; MySQL
  `artikoloj=46669`, `artikoloj_ru=58634`, `sercxo=93552`,
  `sercxo_ru=90298`, `neklaraj=838`, `statistiko=282225`.
- Counts after: PostgreSQL `artikoloj=46669`, `artikoloj_ru=58628`,
  `sercxo=93533`, `sercxo_ru=90303`, `neklaraj=838`; MySQL
  `artikoloj=46669`, `artikoloj_ru=58628`, `sercxo=93553`,
  `sercxo_ru=90305`, `neklaraj=838`, `statistiko=282226`. The six-article
  Russian reduction is identical in both independent importers and matches
  the current source output; all other protected dictionary counts increased
  or stayed stable, and live `statistiko` was preserved.
- Sasha's ready-range metrics in deployed `klarigo.md`: `32247` ready
  Russian–Esperanto articles and `52728` words, range `А — прикраса`. These
  increased from `32237` / `52710` and remain separate from total technical
  table counts.
- `https://rueo.ru/search?query=прикраса`: HTTP 200, `count=1`, article
  present. `https://old.rueo.ru/sercxo/прикраса`: HTTP 200, article present.
  Both `renovigxo` files start with `11 августа 2026 года`.
- Durable state `/home/avo/rueo_master/tmp/rueo_update_active.json` is
  `completed`. No commit, cron/Gateway change, frontend deploy, or unrelated
  mutation was performed.

## 2026-08-08 — prod dictionary refresh to `приколоться`

- Completed the full new + legacy production pipeline with
  `./scripts/rueo_update.sh run-all --last-ru-letter 'приколоться'` through
  durable exec session `57678`. Worker log:
  `/home/avo/rueo_master/tmp/rueo_update_20260808T131844Z.log`.
- Database safety: both production databases on `firstvds-stage` were
  classified as persistent. Before mutation, protected counts were recorded
  and fresh verified snapshots were created:
  `/root/rueo_db_preupdate_20260808T131844Z.dump` (14,775,804 bytes,
  SHA-256
  `e6a81f649852909fef187bf0881aab2639d97aab0c19d01765c22c93162666fd`)
  and `/root/old_rueo_vortaro_preupdate_20260808T131844Z.sql` (55,788,324
  bytes, SHA-256
  `2a2621157d41103eec19d414f043cd7e8fd463f14d089185a879c22a6b07e440`).
  PostgreSQL passed `pg_restore -l`; the MySQL dump has its completion marker
  and includes `statistiko`.
- New PostgreSQL dump:
  `/home/avo/rueo_master/tmp/rueo_db_20260808T132128Z.dump` (14,735,783
  bytes, SHA-256
  `9391fe3576227c0d3d8dfe68057f25e489596a0bf14384597464fda17ddca3f2`,
  `pg_restore -l` passed).
- Legacy backup: `/root/old_rueo_vortaro_20260808T132204Z.sql` (55,788,324
  bytes, SHA-256
  `2ac7316e0b4a7ce3230553d2105e82958f90a95f04960463830dbd1fe7a961ca`).
  Test/prod logs are
  `/var/www/slovari/data/www/updater.rueo.ru/logs/old-rueo-test-20260808T132204Z.log`
  and
  `/var/www/slovari/data/www/updater.rueo.ru/logs/old-rueo-prod-20260808T132204Z.log`.
- Counts before: PostgreSQL `artikoloj=46665`, `artikoloj_ru=58633`,
  `sercxo=93521`, `sercxo_ru=90293`, `neklaraj=838`; MySQL
  `artikoloj=46665`, `artikoloj_ru=58633`, `sercxo=93541`,
  `sercxo_ru=90295`, `neklaraj=838`, `statistiko=282150`.
- Counts after: PostgreSQL `artikoloj=46669`, `artikoloj_ru=58634`,
  `sercxo=93532`, `sercxo_ru=90296`, `neklaraj=838`; MySQL
  `artikoloj=46669`, `artikoloj_ru=58634`, `sercxo=93552`,
  `sercxo_ru=90298`, `neklaraj=838`, `statistiko=282151`. All protected
  dictionary-table counts increased or stayed stable, and live `statistiko`
  was preserved.
- Sasha's ready-range metrics in deployed `klarigo.md`: `32237` ready
  Russian–Esperanto articles and `52710` words, range `А — приколоться`.
  These increased from `32227` / `52699` and remain separate from total
  technical table counts.
- `https://rueo.ru/search?query=приколоться`: HTTP 200, `count=1`, article
  present. `https://old.rueo.ru/sercxo/приколоться`: HTTP 200, article
  present. Both `renovigxo` files start with `8 августа 2026 года`.
- Durable state `/home/avo/rueo_master/tmp/rueo_update_active.json` is
  `completed`. No commit, cron/Gateway change, frontend deploy, or unrelated
  mutation was performed.

## 2026-08-05 — prod dictionary refresh to `приковываться`

- Completed the full new + legacy production pipeline with
  `./scripts/rueo_update.sh run-all --last-ru-letter 'приковываться'` through
  durable exec session `47185`. Worker log:
  `/home/avo/rueo_master/tmp/rueo_update_20260804T212843Z.log`.
- Database safety: both production databases on `firstvds-stage` were
  classified as persistent. Before mutation, protected counts were recorded
  and fresh verified snapshots were created:
  `/root/rueo_db_preupdate_20260804T212843Z.dump` (14,801,333 bytes,
  SHA-256
  `bedec82abcd490348848fce389c72a5926028b89484ef785b8fcda9260a24b95`)
  and `/root/old_rueo_vortaro_preupdate_20260804T212843Z.sql` (55,673,455
  bytes, SHA-256
  `0184173f4a122c0c56e75704befbeb55a8130c9ca0bd2e7b7af93b38de358c2f`).
  PostgreSQL passed `pg_restore -l`; the MySQL dump has its completion marker
  and includes `statistiko`.
- New PostgreSQL dump:
  `/home/avo/rueo_master/tmp/rueo_db_20260804T213139Z.dump` (14,711,980
  bytes, SHA-256
  `4f2d2f35fdc94d45c61d512ccc07916fe4b5475f151f277313bb0b17f250598d`,
  `pg_restore -l` passed).
- Legacy backup: `/root/old_rueo_vortaro_20260804T213214Z.sql` (55,673,455
  bytes, SHA-256
  `d3c98cd16943b48f8d7307fe3f26765974ff3e5a1ee5720831d686a05ea8b70e`).
  Test/prod logs are
  `/var/www/slovari/data/www/updater.rueo.ru/logs/old-rueo-test-20260804T213214Z.log`
  and
  `/var/www/slovari/data/www/updater.rueo.ru/logs/old-rueo-prod-20260804T213214Z.log`.
- Counts before: PostgreSQL `artikoloj=46663`, `artikoloj_ru=58645`,
  `sercxo=93516`, `sercxo_ru=90319`, `neklaraj=838`; MySQL
  `artikoloj=46663`, `artikoloj_ru=58645`, `sercxo=93536`,
  `sercxo_ru=90321`, `neklaraj=838`, `statistiko=280705`.
- Counts after: PostgreSQL `artikoloj=46665`, `artikoloj_ru=58633`,
  `sercxo=93521`, `sercxo_ru=90293`, `neklaraj=838`; MySQL
  `artikoloj=46665`, `artikoloj_ru=58633`, `sercxo=93541`,
  `sercxo_ru=90295`, `neklaraj=838`, `statistiko=280706` after verification.
  The 12-article Russian reduction is identical in both independent importers
  and matches the current source, while live `statistiko` was preserved.
- Sasha's ready-range metrics in deployed `klarigo.md`: `32227` ready
  Russian–Esperanto articles and `52699` words, range
  `А — приковываться`. These increased from `32225` / `52692` and remain
  separate from total technical table counts.
- `https://rueo.ru/search?query=приковываться`: HTTP 200, `count=1`, article
  present. `https://old.rueo.ru/sercxo/приковываться`: HTTP 200, article
  present. Both `renovigxo` files start with `5 августа 2026 года`.
- Durable state `/home/avo/rueo_master/tmp/rueo_update_active.json` is
  `completed`. No commit, cron/Gateway change, frontend deploy, or unrelated
  mutation was performed.

## 2026-08-03 — production `rueo.ru` switched to TLS 1.2-only

- Sasha authorized the second, separate protocol experiment after HTTP/2 was
  enabled across Stage. Changed only production `rueo.ru` from
  `ssl_protocols TLSv1.2 TLSv1.3;` to `ssl_protocols TLSv1.2;` at 22:42 MSK.
- Hash comparison across all nginx vhosts confirmed that only
  `/etc/nginx/vhosts/slovari/rueo.ru.conf` changed; its exact diff removes only
  the `TLSv1.3` token. Backup and verification artifacts:
  `/root/rueo-tls12-backups/20260803-224238`.
- `rueo.ru` returns HTTP 200 over HTTP/2 + TLS 1.2 and forced HTTP/1.1 + TLS
  1.2. `/`, `/package.json`, `/news.md`, `/status/info`, search, and suggestions
  all return HTTP/2 200. Forced TLS 1.3 now fails with the expected protocol
  version alert. Three control sites still return HTTP/2 200 over TLS 1.3.
- `nginx -t`, reload, active-service, and journal checks passed. No other vhost,
  TLS profile, certificate, application, database, ISPmanager setting, or
  commit changed.
- The August 3 traffic report was generated before this switch and is a
  pre-experiment reference. Evaluate TLS 1.2-only using August 4 onward and
  visitor feedback; do not attribute the earlier traffic rise to this change.

## 2026-08-03 — HTTP/2 experiment extended to all Stage HTTPS vhosts

- The isolated `rueo.ru` HTTP/2 phase completed two full daily reporting
  cycles without an availability regression; human requests rose from 12,568
  on August 1 to 14,164 on August 2 and 15,750 on August 3, while unique IPs
  remained in the same broad range (542, 468, 505). Treat this as evidence of
  no obvious breakage, not proof that HTTP/2 caused the traffic increase.
- Sasha authorized a whole-Stage rollout. Added `http2 on;` to the remaining
  20 nginx TLS vhosts, bringing all 21 current HTTPS vhosts to HTTP/2. The
  existing `rueo.ru` config itself was unchanged in this rollout.
- Every HTTPS vhost negotiated HTTP/2 and retained forced HTTP/1.1 with its
  same pre-change status code. `nginx -t`, reload, service state, and journal
  checks passed; representative sites still negotiate both TLS 1.2 and 1.3.
- Server backup and verification artifacts:
  `/root/stage-http2-backups/20260803-223608`. No TLS setting, certificate,
  application, database, ISPmanager global setting, or commit was changed.
- Continue ordinary monitoring. Any future TLS 1.2-only test remains a
  separate phase and should not be inferred from this rollout.

## 2026-08-01 — isolated HTTP/2 experiment on production `rueo.ru`

- Sasha authorized a narrow HTTP/2 experiment on `rueo.ru`. The ISPmanager
  HTTP/2 switch was deliberately not used because it is server-wide and the
  managed vhosts contain custom configuration.
- Added only `http2 on;` to the TLS server block in
  `/etc/nginx/vhosts/slovari/rueo.ru.conf`. A complete before-copy and
  verification artifacts are in
  `/root/rueo-http2-backups/20260801-203240`.
- Hash comparison across every file under `/etc/nginx/vhosts` confirmed that
  only `rueo.ru.conf` changed. `nginx -t` passed, nginx reloaded cleanly and
  remains active.
- External checks: `/`, `/package.json`, `/news.md`, `/status/info`, a valid
  `/search?query=test`, and `/suggest?term=test` all return HTTP 200 over
  HTTP/2. Forced HTTP/1.1 remains HTTP 200, so the compatibility fallback is
  intact. TLS 1.2 and TLS 1.3 both still negotiate with the same strong
  ciphers as before. `teatrzazerkalye.ru` remains HTTP/1.1, proving the change
  did not spill into another vhost.
- This first phase changes HTTP negotiation only. Do not disable TLS 1.3 until
  the HTTP/2-only experiment has been observed through daily traffic reports
  and real visitor feedback. No application code, database, ISPmanager global
  setting, certificate, or other vhost was changed.

## 2026-08-01 — prod dictionary refresh to `приключиться`

- Completed the full new + legacy production pipeline with
  `./scripts/rueo_update.sh run-all --last-ru-letter 'приключиться'`.
  Worker log:
  `/home/avo/rueo_master/tmp/rueo_update_20260731T214756Z.log`.
- Database safety: both production databases on `firstvds-stage` were
  classified as persistent. Before mutation, protected counts were recorded
  and fresh verified snapshots were created:
  `/root/rueo_db_preupdate_20260731T214926Z.dump` (14,767,414 bytes,
  SHA-256
  `572546d88c52aa6c8b292c0984f71e6ebd5c58ce564f9afbc720a26133ce3a56`)
  and `/root/old_rueo_vortaro_preupdate_20260731T214926Z.sql` (55,621,634
  bytes, SHA-256
  `fe7bb9f5fcb18981fe782539768abcf7ea0248814988fcedd6d173d681d5a002`).
  PostgreSQL was validated with `pg_restore -l`; the MySQL dump is complete
  and includes `statistiko`.
- New PostgreSQL dump:
  `/home/avo/rueo_master/tmp/rueo_db_20260731T215203Z.dump` (14,727,310
  bytes, SHA-256
  `2b4a6246cb7ae663033424d6d615ff2341392283edb0117de436b7d02bfc4f27`,
  `pg_restore -l` passed).
- Legacy backup: `/root/old_rueo_vortaro_20260731T215239Z.sql` (55,621,634
  bytes, SHA-256
  `595c8f764542578b22588c09fb2169edcb9f404e56b5ed961f2457fd453b8fe4`).
  Test/prod logs are
  `/var/www/slovari/data/www/updater.rueo.ru/logs/old-rueo-test-20260731T215239Z.log`
  and
  `/var/www/slovari/data/www/updater.rueo.ru/logs/old-rueo-prod-20260731T215239Z.log`.
- Counts before: PostgreSQL `artikoloj=46660`, `artikoloj_ru=58650`,
  `sercxo=93508`, `sercxo_ru=90314`, `neklaraj=838`; MySQL
  `artikoloj=46660`, `artikoloj_ru=58650`, `sercxo=93528`,
  `sercxo_ru=90316`, `neklaraj=838`, `statistiko=280104`.
- Counts after: PostgreSQL `artikoloj=46663`, `artikoloj_ru=58645`,
  `sercxo=93516`, `sercxo_ru=90319`, `neklaraj=838`; MySQL
  `artikoloj=46663`, `artikoloj_ru=58645`, `sercxo=93536`,
  `sercxo_ru=90321`, `neklaraj=838`, `statistiko=280104` before verification
  and `280105` after the legacy HTTP check. The five-article reduction in the
  Russian total is identical in both independent importers and matches the
  current source, while the live `statistiko` table was preserved.
- Sasha's ready-range metrics in deployed `klarigo.md`: `32225` ready
  Russian–Esperanto articles and `52692` words, range `А — приключиться`.
  These both increased from the preceding `32218` / `52671` and remain
  separate from total technical table counts.
- `https://rueo.ru/search?query=приключиться`: HTTP 200, `count=1`, article
  present. `https://old.rueo.ru/sercxo/приключиться`: HTTP 200, article
  present. Both `renovigxo` files start with `1 августа 2026 года`.
- Durable state `/home/avo/rueo_master/tmp/rueo_update_active.json` is
  `completed`. No commit, cron/Gateway change, frontend deploy, or unrelated
  mutation was performed.

Updated: 2026-07-29 00:46 (Europe/Moscow)

## 2026-07-29 — prod dictionary refresh to `прикладной`

- Completed the full new + legacy production pipeline with
  `./scripts/rueo_update.sh run-all --last-ru-letter 'прикладной'`.
- Database safety: both production databases on `firstvds-stage` were
  classified as persistent. Before mutation, recorded counts and created
  verified snapshots
  `/root/rueo_db_preupdate_20260728T213746Z.dump` (14,822,519 bytes,
  SHA-256
  `6f1bc77ca0e9ddf041222322d101b2e8899c4149a28627dd984108a6ec04e2da`)
  and `/root/old_rueo_vortaro_preupdate_20260728T213746Z.sql` (55,570,922
  bytes, SHA-256
  `62cf75b42d06b3a772ec7a8be98f614105670e5e41fcf22c4ac233ddff86a9d0`).
- The first worker attempt failed during local importer bootstrap because the
  host Python lacked `SQLAlchemy`; no DB mutation, dump, restore, or legacy
  stage had started. Installed the existing `backend/requirements.txt` into
  the system Python user site and verified the importer. A detached shell was
  then reaped during local Esperanto import, still before any production
  mutation. The durable exec session `41964` completed the full pipeline.
  Final worker log:
  `/home/avo/rueo_master/tmp/rueo_update_20260728T214205Z.log`.
- New PostgreSQL dump:
  `/home/avo/rueo_master/tmp/rueo_db_20260728T214411Z.dump` (14,703,879
  bytes, SHA-256
  `92d1027bc3d03515a0807145a0040b893580659e91cc2998bb5e46790806fc9d`).
- Legacy backup: `/root/old_rueo_vortaro_20260728T214503Z.sql` (55,570,922
  bytes, SHA-256
  `3bb7cceac58bda1708cd242d5fc1146b6a0a82bbdff6c80bd7c6bb1644c3b772`).
  Test/prod logs are
  `/var/www/slovari/data/www/updater.rueo.ru/logs/old-rueo-test-20260728T214503Z.log`
  and
  `/var/www/slovari/data/www/updater.rueo.ru/logs/old-rueo-prod-20260728T214503Z.log`.
- Counts after: PostgreSQL `artikoloj=46660`, `artikoloj_ru=58650`,
  `sercxo=93508`, `sercxo_ru=90314`, `neklaraj=838`; MySQL
  `artikoloj=46660`, `artikoloj_ru=58650`, `sercxo=93528`,
  `sercxo_ru=90316`, `neklaraj=838`, `statistiko=279520`. The Russian article
  count is 8 below the preceding production state in both independent
  importers and exactly matches the current source output, so this is not a
  target restore loss. A lower article count is a normal possible source
  change: the draft contains an automatic inversion of the Esperanto–Russian
  dictionary, and the author may consolidate many generated draft articles
  into one edited article. Live `statistiko` was preserved and rose from
  `279519` to `279520` during verification.
- Keep two Russian–Esperanto metrics distinct in future reports:
  `artikoloj_ru=58650` is the total imported table count including generated
  draft inversions, while Sasha's progress statistic is the ready range shown
  in the new site's `klarigo.md`. For this update that progress statistic is
  `32218` ready articles and `52671` words in them; Sasha confirmed that both
  increased. Future dictionary-update reports should record these ready-range
  figures separately from database integrity counts.
- `https://rueo.ru/search?query=прикладной`: HTTP 200, `count=1`, article
  present. `https://old.rueo.ru/sercxo/прикладной`: HTTP 200, article present.
  Both `renovigxo` files start with `29 июля 2026 года`.
- Durable project state:
  `/home/avo/rueo_master/tmp/rueo_update_active.json` is `completed`. No
  commit, cron/Gateway change, or unrelated frontend deploy was performed.

Updated: 2026-07-23 02:15 (Europe/Moscow)

## 2026-07-23 — prod dictionary refresh to `прикид`

- Completed the full new + legacy production pipeline with
  `./scripts/rueo_update.sh run-all --last-ru-letter 'прикид'`.
- Database safety: both server targets were classified as persistent. Before
  mutation, recorded PostgreSQL/MySQL counts and created verified snapshots
  `/root/rueo_db_preupdate_20260722T230814Z.dump` (14,745,643 bytes) and
  `/root/old_rueo_vortaro_preupdate_20260722T230814Z.sql` (55,400,988 bytes).
- The first detached attempt, PID `884671`, exited during local sync-in before
  importer/restore/legacy work or production DB mutation. Recovery confirmed
  no remaining process; exec session `89711` then completed normally. Worker
  log: `/home/avo/rueo_master/tmp/rueo_update_20260722T230814Z.log`.
- New PostgreSQL dump:
  `/home/avo/rueo_master/tmp/rueo_db_20260722T231224Z.dump` (14,716,476 bytes,
  SHA-256 `2f44860286205829d7b52c436c71a7440bef1edf1d7ae5010cabab1daffeb95c`).
- Legacy backup: `/root/old_rueo_vortaro_20260722T231250Z.sql` (55,401,067
  bytes, SHA-256
  `f274f2a881103f0a01d9aaf1d690291c182f5fc49f919a7ff2d321c9de77808a`).
  Test/prod logs end in `old-rueo-test-20260722T231250Z.log` and
  `old-rueo-prod-20260722T231250Z.log` under the updater log directory.
- Counts after: PostgreSQL `artikoloj=46658`, `artikoloj_ru=58658`,
  `sercxo=93499`, `sercxo_ru=90314`, `neklaraj=838`; MySQL
  `artikoloj=46658`, `artikoloj_ru=58658`, `sercxo=93519`,
  `sercxo_ru=90316`, `neklaraj=838`. The Russian article count is 10 below the
  previous run in both independent importers and exactly matches current source
  output, so it is not an unexplained target loss. Live `statistiko` remained
  populated and rose from `277383` before to `277384`, then `277385` during
  verification traffic.
- `https://rueo.ru/search?query=прикид`: HTTP 200, `count=1`, contains the new
  article. `https://old.rueo.ru/sercxo/прикид`: HTTP 200 and contains the
  article. Both `renovigxo` files start with `23 июля 2026 года`.
- Updated `/home/avo/clawd/.active-task.json` to `completed`. No Gateway/cron
  change or frontend deploy was performed. This handoff change is uncommitted;
  the preceding approved commits remain `2a863c6` and `eb646a4`.

Updated: 2026-07-23 02:08 (Europe/Moscow)

## 2026-07-23 — real Reformal duplicate-link mail handled

- UID `1147`, the reply to feedback `ia=1220746` / «Заумь», exposed two
  real-template cases that the strict parser had classified as
  `missing_reformal_ia`: the same exact `ia` project URL appeared twice, and
  ordinary Reformal project-home URLs without an `ia` appeared beside it.
- Updated `/home/avo/clawd/research/youtrack/rueo_mail_ingest.py` to accept
  repeated occurrences only when every extracted numeric `ia` is identical,
  continue rejecting duplicate query parameters and conflicting/invalid
  values, and ignore supported project-home links that contain no `ia`.
- Added reply-title extraction from the exact linked feedback anchor (with a
  doubled-quote subject fallback). Root lookup now searches by `ia` and the
  feedback-title hint, then still requires the candidate description to
  contain the exact supported URL and unique root-feedback evidence.
- Expanded the mock-only suite from 19 to 22 tests; `py_compile` and all 22
  tests pass. A live read-only preview resolved exactly one mutable message:
  UID `1147` -> comment on legacy root `eoru-1170`; the other 49 messages were
  `skip_seen`.
- Applied the targeted inbox batch after Sasha's approval. YouTrack created
  comment `4-439` on `eoru-1170`; readback confirms the full reply and durable
  message marker. Local state stores `ia=1220746 -> eoru-1170`, and a rerun is
  now `skip_seen`. The issue remained `Fixed`; no standalone RUEO issue or
  duplicate was created.
- Implementation code, tests, and task artifacts were committed in the
  OpenClaw workspace as `2a863c6` (`Harden Rueo Reformal mail threading`). No
  database command, cron mutation/run, deploy, or Gateway restart was
  performed.

Updated: 2026-07-22 01:16 (Europe/Moscow)

## 2026-07-22 — eight technical eoru duplicates deleted after approval

- Sasha explicitly approved deletion in Telegram confirmation topic message
  `21965`.
- Saved a full pre-delete JSON snapshot for `eoru-1454` through `eoru-1461`
  and the preserved canonical issues `RUEO-44` through `RUEO-51` at
  `/home/avo/clawd/backups/youtrack/eoru-technical-duplicates-20260722T011542/`.
- Deleted exactly `eoru-1454`, `eoru-1455`, `eoru-1456`, `eoru-1457`,
  `eoru-1458`, `eoru-1459`, `eoru-1460`, and `eoru-1461`.
- Post-delete readback returned HTTP 404 for all eight deleted issues and HTTP
  200 for every canonical `RUEO-44` through `RUEO-51`; canonical issues were
  not changed. No commit, deploy, database operation, or Gateway restart was
  performed.

## 2026-07-22 — eoru-1462 pagination hardening completed

- Implemented bounded exhaustive YouTrack issue search and per-candidate
  comment pagination in `/home/avo/clawd/research/youtrack/rueo_mail_ingest.py`.
  Completion now requires an empty terminal page; malformed, repeated, failed,
  conflicting, or bound-exhausted pagination fails closed into the existing
  retryable manual-review path before mutation.
- Preserved strict supported legacy/current Reformal URL parsing and exact `ia`
  filtering; message-marker matching now also rejects longer-token prefix
  matches and markers adjacent to Cyrillic/other Unicode word characters.
  Embedded issue comment subsets are no longer trusted. Malformed comment ids
  or text (including null/non-string text) now fail the idempotency lookup into
  retryable `manual_review` before any create/comment mutation.
- Expanded the fake/request-only suite from 11 to 19 tests: multi-page issues,
  multi-page comments, legacy `.ru` fallback, exact marker filtering,
  duplicate/ambiguous candidates, failed/malformed/repeated pagination, and
  bound exhaustion, plus malformed comment identity/text no-mutation and
  Unicode-boundary regressions. `py_compile` and all 19 tests pass.
- Implementation artifact:
  `/home/avo/clawd/memory-bank/tasks/2026-07-22-eoru-1462-pagination-hardening.md`.
  The first review's two major findings were corrected. A fresh final
  independent re-review passed with no critical, major, or minor findings;
  `py_compile`, all 19 mock-only tests, and 4 independent edge probes passed.
- Workboard card `4f5e6667-228f-4228-b8e8-f9d42ff725a6` is `done`; YouTrack
  `eoru-1462` is `Fixed` with `resolved=1784672423588`. The routed completion
  report receipt is Telegram message `21968`; the first-review failure receipt
  is message `21960`.
- No additional substantial follow-up was identified. No network, live
  importer, historical YouTrack mutation, database, cron run, commit, deploy,
  or production action was performed.

## 2026-07-22 — approved eoru-1426 follow-up package applied

- Sasha approved the exact package in Telegram confirmation topic message
  `21953` and explicitly declined a separate Stardict/licensing product task.
- Rewrote `eoru-1462` to require stable Reformal `ia`, supported legacy/current
  URL fallback, exhaustive bounded issue and comment pagination, fail-closed
  handling, and mock-only pagination/ambiguity/failure tests. Readback confirms
  `State=In Progress`, unresolved, with `dev-board`; it is dispatcher-eligible.
- Rewrote `eoru-1463` as minimal deduplication only. Pre-mutation readback
  showed open RUEO-11 and terminal Verified eoru-1232 with no duplicate link.
  Applied exactly one `RUEO-11 duplicates eoru-1232` link, read it back, then
  closed RUEO-11 as `Duplicate` (`resolved=1784670588872`). No text/comment was
  copied into eoru-515 and nothing was deleted. Follow-up eoru-1463 is `Fixed`
  (`resolved=1784670606022`).
- Rewrote `eoru-1464` as minimal deduplication only. Pre-mutation readback
  showed open RUEO-12 and terminal Won't fix eoru-1233 with no duplicate link.
  Applied exactly one `RUEO-12 duplicates eoru-1233` link, read it back, then
  closed RUEO-12 as `Duplicate` (`resolved=1784670589358`). No absent root was
  searched for or created and nothing was deleted. Follow-up eoru-1464 is
  `Fixed` (`resolved=1784670606166`).
- The first braced state-command attempts for eoru-1462 failed HTTP 400 without
  state mutation; the accepted YouTrack command syntax was `State In Progress`.
  `dev-board` applied successfully and final readback converged. No code,
  database, commit, deploy, cron, production, or Gateway change occurred.

Updated: 2026-07-22 01:58 (Europe/Moscow)

## 2026-07-22 — meaning of long-lived eoru dictionary tails

- The Russian–Esperanto dictionary is authored sequentially by Russian
  alphabet. At each dictionary refresh Sasha supplies the last completed
  Russian headword; material after that boundary is explicitly draft even
  though readers often report its missing words/translations as defects.
- Do not treat every old `eoru` issue in `In Progress` as forgotten executable
  work. The historical backlog mixes: noise about not-yet-completed articles;
  useful headword/translation proposals worth considering early; and genuine
  lexicographic questions for which the author has not supplied an answer.
- A report only stating that a post-boundary draft article is incomplete can
  normally be closed with an explanatory comment. A concrete useful lexical
  proposal may remain for review even before its article is complete. Questions
  awaiting the author must stay human-owned and must not be auto-resolved or
  dispatched as implementation work.
- `eoru-963` is reserved for Sasha to discuss with the author on 2026-07-22.
  `eoru-532` and `eoru-681` are examples of unresolved author-dependent lexical
  questions. Sasha confirmed `eoru-865`, `eoru-835`, `eoru-822`, `eoru-806`,
  `eoru-743`, `eoru-610`, and `eoru-536` are already done and closed them in
  YouTrack.
- Prefer `In Progress` only for genuinely active work. Long-term author review
  should remain visibly human-gated (for example `Open` plus an agreed author-
  review marker) rather than silently entering the technical dispatcher queue.

## 2026-07-21 — eoru-1426 durable Reformal threading corrected after review

- The fix2 worker was interrupted after partial code/test, cron-prompt, report,
  and handoff changes had landed. Lease-backed fix3 inspected and preserved the
  correct partial artifacts, completed focused/full local validation, and read
  back both cron contracts. Final independent re-review passed with no critical
  or major findings.
- Hardened `/home/avo/clawd/research/youtrack/rueo_mail_ingest.py`: stable
  Reformal `ia` is now parsed strictly from one exact supported host/project
  URL with one numeric query parameter; embedded, duplicate, conflicting,
  nonnumeric, hostile-host, and ambiguous URL inputs fail closed. Root recovery
  continues from local message/root state and exact existing
  YouTrack evidence, fail-closed `manual_review` for missing/unknown/ambiguous
  roots, durable per-message markers for remote idempotency, atomic state saves,
  and deterministic top-level JSON-array stdout/logs.
- Added eleven fixture/fake-only tests covering feedback-to-root,
  reply-to-comment, empty-state YouTrack recovery, unknown and ambiguous roots,
  crash-style rerun recovery, supported legacy/current URLs, adversarial `ia`
  inputs, wrong-root prevention, and cron output shape. No
  network, IMAP, database, live ingest, or YouTrack mutation was used.
- Updated only the prompts of the existing Rueo 08:00/20:00 cron jobs
  (`773fc811-b511-4ace-af65-696a3d408da3`,
  `c1fee467-50ee-4399-b265-88930f748bab`). They now require top-level-array
  inspection (never `.items`) and a Rueo-topic notice for every ingest
  `manual_review` with the exact retry reason and available root evidence.
  Readback preserved schedule/model/delivery/routing/failure-alert fields; the
  jobs were not run.
- Read-only reconciliation preview:
  `/home/avo/clawd/research/youtrack/eoru-1426-rueo-11-12-reconciliation-preview.json`.
  `RUEO-11` likely belongs on `eoru-515` (same `ia=1054059`, explicit root
  feedback evidence); `RUEO-12` remains unresolved because its only preserved
  same-`ia=237217` match, `eoru-1233`, is itself comment-shaped. The artifact
  contains exact non-applied plans; neither historical issue was changed.
- Recovery report:
  `/home/avo/clawd/memory-bank/tasks/2026-07-21-eoru-1426-reformal-threading.md`.
  The two first-review major findings are corrected and independently verified.
  Follow-ups were split into `eoru-1462` (execution-ready pagination hardening),
  `eoru-1463` (human-gated `RUEO-11 -> eoru-515` migration), and `eoru-1464`
  (human-gated root decision for `RUEO-12`). All are `Open` without `dev-board`;
  no historical migration was performed.

## 2026-07-21 — reconciled eoru-1424/1425/1426 with live RUEO mail ingest

- `eoru-1424` is now `Verified`: the preview/apply helper and guarded
  autoclean exist, the safe historical HTML cleanup was completed, and the
  08:00/20:00 maintenance contour remains active.
- `eoru-1425` is now `Won't fix` as a separate historical batch: its old eoru
  fixtures remain preserved, while the useful current threading work was
  consolidated into `eoru-1426`.
- `eoru-1426` was rewritten around the remaining live gap and moved to
  `In Progress` with `dev-board`. Current evidence: 52 handled mailbox
  messages, 7 known Reformal roots, and comment `4-317` correctly attached to
  `RUEO-23`; however `RUEO-11` and `RUEO-12` remain standalone replies because
  their roots were absent from the local state file.
- Acceptance now requires durable root recovery, fail-closed manual review for
  unknown roots, idempotency tests, a read-only reconciliation preview for
  `RUEO-11/12`, and deterministic cron summaries. Historical YouTrack data,
  production, commit, and deploy are outside autonomous apply scope.
- Dispatcher gate readback is eligible/ready with no blockers or active card;
  the enabled 15-minute dispatcher may claim `eoru-1426` on its next queue
  pass. No worker had claimed it at this checkpoint.

## 2026-07-20 — prod dictionary refresh to `прикармливать`

Dictionary refresh completed on prod to last Russian word `прикармливать`, including the legacy old.rueo.ru contour.

Command and supervision:
- `./scripts/rueo_update.sh run-all --last-ru-letter 'прикармливать'`
- Durable worker PID `65391`; supervisor log `/home/avo/rueo_master/tmp/rueo_update_20260719T223523Z.log`.
- Worker log lifetime: `01:35:52`–`01:39:31` MSK, about `3m 40s` total.
- New PostgreSQL dump was ready after about `1m 51s`; the remaining server restore/deploy plus legacy test/backup/prod contour completed by `3m 40s`.

Database safety and counts:
- Both target databases were classified as persistent before the run; pre-run counts and prior snapshots were recorded in `/home/avo/clawd/.active-task.json`.
- New PostgreSQL counts after run: `artikoloj 46657`, `artikoloj_ru 58668`, `sercxo 93497`, `sercxo_ru 90311`, `neklaraj 838`.
- Legacy MySQL counts after run: `artikoloj 46657`, `artikoloj_ru 58668`, `sercxo 93517`, `sercxo_ru 90313`, `neklaraj 838`, `statistiko 276652`.
- No protected-table count unexpectedly decreased; `statistiko` remained populated (`276650` before, `276652` after).

Artifacts and verification:
- New-site dump: `/home/avo/rueo_master/tmp/rueo_db_20260719T223742Z.dump` (`14693692` bytes).
- Legacy backup: `/root/old_rueo_vortaro_20260719T223807Z.sql` (`55336708` bytes).
- Legacy test log: `/var/www/slovari/data/www/updater.rueo.ru/logs/old-rueo-test-20260719T223807Z.log`.
- Legacy prod log: `/var/www/slovari/data/www/updater.rueo.ru/logs/old-rueo-prod-20260719T223807Z.log`.
- `https://rueo.ru/search?query=прикармливать`: HTTP `200`, JSON `count: 1`, curl total `0.696382s`.
- `https://old.rueo.ru/sercxo/прикармливать`: HTTP `200`, page contains the word/article, curl total `0.566023s`.
- Both new and old `renovigxo` files start with `20 июля 2026 года`.

No commit was made. Current intentional local changes remain uncommitted; include `memory-bank/*` in the next approved commit per workspace rule.

## 2026-07-15 — prod dictionary refresh to `прийтись`

Dictionary refresh completed on prod to last Russian word `прийтись`, including the legacy old.rueo.ru contour.

Command:
- `./scripts/rueo_update.sh run-all --last-ru-letter 'прийтись'`

New rueo.ru pipeline:
- Dropbox sync-in, local import, sync-back, dump, server restore, and `tekstoj` deploy completed on `firstvds-stage`.
- New-site PostgreSQL dump kept at: `/home/avo/rueo_master/tmp/rueo_db_20260714T232156Z.dump`.
- Import/server counts: EO articles `46655`, RU articles `58667`, EO search `93489`, RU search `90304`, fuzzy `838`.
- Verification: `https://rueo.ru/search?query=прийтись` returned HTTP `200`, JSON `count: 1`.
- New `renovigxo.md` starts `15 июля 2026 года`.

old.rueo.ru legacy update:
- Backup: `/root/old_rueo_vortaro_20260714T232222Z.sql`.
- Test log: `/var/www/slovari/data/www/updater.rueo.ru/logs/old-rueo-test-20260714T232222Z.log`.
- Prod log: `/var/www/slovari/data/www/updater.rueo.ru/logs/old-rueo-prod-20260714T232222Z.log`.
- Legacy table counts after run: `artikoloj 46655`, `artikoloj_ru 58667`, `sercxo 93509`, `sercxo_ru 90306`, `neklaraj 838`, `statistiko 273340`.
- `statistiko` was not truncated by the importer and remains populated.
- Verification: `https://old.rueo.ru/sercxo/прийтись` returned HTTP `200` and contains the word/article.
- Old `renovigxo.textile` starts `15 июля 2026 года`.

No commit was made. Current intentional local changes include previous script default updates and memory docs; include `memory-bank/*` in the next approved commit per workspace rule.

## 2026-07-09 — prod dictionary refresh to `приисковый`

Dictionary refresh completed on prod to last Russian word `приисковый`, including the legacy old.rueo.ru contour.

Command:
- `./scripts/rueo_update.sh run-all --last-ru-letter 'приисковый'`

New rueo.ru pipeline:
- Dropbox sync-in, local import, sync-back, dump, server restore, and `tekstoj` deploy completed on `firstvds-stage`.
- New-site PostgreSQL dump kept at: `/home/avo/rueo_master/tmp/rueo_db_20260708T211844Z.dump`.
- Import/server counts: EO articles `46652`, RU articles `58672`, EO search `93474`, RU search `90302`, fuzzy `838`.
- Verification: `https://rueo.ru/search?query=приисковый` returned HTTP `200`, JSON `count: 1`.
- New `renovigxo.md` starts `9 июля 2026 года`.

old.rueo.ru legacy update:
- Backup: `/root/old_rueo_vortaro_20260708T211910Z.sql`.
- Test log: `/var/www/slovari/data/www/updater.rueo.ru/logs/old-rueo-test-20260708T211910Z.log`.
- Prod log: `/var/www/slovari/data/www/updater.rueo.ru/logs/old-rueo-prod-20260708T211910Z.log`.
- Legacy table counts after run: `artikoloj 46652`, `artikoloj_ru 58672`, `sercxo 93494`, `sercxo_ru 90304`, `neklaraj 838`, `statistiko 269618`.
- `statistiko` was not truncated by the importer and remains populated.
- Verification: `https://old.rueo.ru/sercxo/приисковый` returned HTTP `200` and contains the word/article.
- Old `renovigxo.textile` starts `9 июля 2026 года`.

No commit was made. Current intentional local changes include previous script default updates and memory docs; include `memory-bank/*` in the next approved commit per workspace rule.

## 2026-07-06 — prod dictionary refresh to `призывать`

Dictionary refresh completed on prod to last Russian word `призывать`, including the legacy old.rueo.ru contour.

Evening follow-up:
- Sasha noticed the 20:00 Rueo YouTrack mail ingest report was landing in the default direct/main Telegram stream instead of the rueo.ru topic.
- Root cause: both OpenClaw cron jobs (`08:00` id `773fc811-b511-4ace-af65-696a3d408da3`, `20:00` id `c1fee467-50ee-4399-b265-88930f748bab`) had `delivery.mode=none` without `threadId`, and their prompts only said to send Sasha a Telegram message.
- Updated both cron payload prompts to require OpenClaw `message(action="send", target="telegram:2631113", threadId="361351")` for any user-visible Rueo YouTrack maintenance notice.
- Also set both jobs' inactive `delivery` metadata to `channel=telegram`, `to=telegram:2631113`, `threadId=361351`, `bestEffort=true` for clarity. The cron API rejected `threadId` under `failureAlert`, so failure alerts may still use the generic direct route; normal created-issue reports should now go to the rueo.ru topic.

Command:
- `./scripts/rueo_update.sh run-all --last-ru-letter 'призывать'`

New rueo.ru pipeline:
- Dropbox sync-in, local import, sync-back, dump, server restore, and `tekstoj` deploy completed on `firstvds-stage`.
- New-site PostgreSQL dump kept at: `/home/avo/rueo_master/tmp/rueo_db_20260705T215853Z.dump`.
- Import/server counts: EO articles `46651`, RU articles `58697`, EO search `93468`, RU search `90329`, fuzzy `838`.
- Verification: `https://rueo.ru/search?query=призывать` returned HTTP `200`, JSON `count: 1`.
- New `renovigxo.md` starts `6 июля 2026 года`.

old.rueo.ru legacy update:
- Backup: `/root/old_rueo_vortaro_20260705T215918Z.sql`.
- Test log: `/var/www/slovari/data/www/updater.rueo.ru/logs/old-rueo-test-20260705T215918Z.log`.
- Prod log: `/var/www/slovari/data/www/updater.rueo.ru/logs/old-rueo-prod-20260705T215918Z.log`.
- Legacy table counts after run: `artikoloj 46651`, `artikoloj_ru 58697`, `sercxo 93488`, `sercxo_ru 90331`, `neklaraj 838`, `statistiko 268647`.
- `statistiko` was not truncated by the importer and remains populated.
- Verification: `https://old.rueo.ru/sercxo/призывать` returned HTTP `200` and contains the word/article.
- Old `renovigxo.textile` starts `6 июля 2026 года`.

No commit was made. Current intentional local changes include previous script default updates and memory docs; include `memory-bank/*` in the next approved commit per workspace rule.

## 2026-07-04 — prod dictionary update to `призывать` after FirstVDS move

Dictionary update completed on prod to last Russian word `призывать`, including the legacy old.rueo.ru contour on the new FirstVDS Stage server.

Pre-flight fix:
- Checked the `rueo_update` skill before the run. It still pointed the project scripts at the old Timeweb origin `root@72.56.13.203`.
- Updated local defaults to the working SSH alias `firstvds-stage` in:
  - `scripts/rueo_update.sh`
  - `scripts/deploy_frontend_pwa.sh`
  - `memory-bank/FRONTEND_DEPLOYMENT.md`
- Also updated `/home/avo/clawd/skills/rueo_update/SKILL.md` so its frontend target note no longer names the old target.
- Verified `bash -n` and help output: both `SERVER_SSH` and `OLD_UPDATER_SSH` now default to `firstvds-stage`.

New rueo.ru pipeline:
- Command: `./scripts/rueo_update.sh run --last-ru-letter 'призывать'`.
- New-site PostgreSQL dump kept at: `/home/avo/rueo_master/tmp/rueo_db_20260703T213051Z.dump`.
- Import counts: EO articles `46650`, RU articles `58743`, EO search `93462`, RU search `90375`, fuzzy `838`.
- Tracking summary: EO changed `18`, auto-dated `9`, new `10`; RU changed `49`, auto-dated `48`, new `12`.
- Server restore and `tekstoj` deploy completed on `firstvds-stage`.
- Verification: `https://rueo.ru/search?query=призывать` returned HTTP `200`, JSON `count: 1`.
- New `renovigxo.md` starts `4 июля 2026 года`.

old.rueo.ru legacy update:
- First `run-old` on the new server exposed missing migration pieces:
  - `slovari_vuser` lacked access to `slovari_vortaro_test`;
  - `slovari_vortaro_test` did not exist with the old updater schema.
- Fixed on `firstvds-stage` by creating `slovari_vortaro_test`, granting `slovari_vuser` the same dictionary-table privileges for the test DB, and loading schema-only structure from `slovari_vortaro`.
- Schema backup before loading test DB schema: `/root/old-rueo-testdb-schema-backups/slovari_vortaro_schema_20260703T213251Z.sql`.
- Successful command after fixes: `./scripts/rueo_update.sh run-old --last-ru-letter 'призывать'`.
- Backup: `/root/old_rueo_vortaro_20260703T213337Z.sql`.
- Test log: `/var/www/slovari/data/www/updater.rueo.ru/logs/old-rueo-test-20260703T213337Z.log`.
- Prod log: `/var/www/slovari/data/www/updater.rueo.ru/logs/old-rueo-prod-20260703T213337Z.log`.
- Legacy table counts after run: `artikoloj 46650`, `artikoloj_ru 58743`, `sercxo 93482`, `sercxo_ru 90377`, `neklaraj 838`, `statistiko 268498`.
- `statistiko` was not truncated by the importer and remains populated.
- Verification: `https://old.rueo.ru/sercxo/призывать` returned HTTP `200` and contains the word/article.
- Old `renovigxo.textile` starts `4 июля 2026 года`.

No commit was made. Current intentional local changes include the two script default updates and memory docs; include `memory-bank/*` in the next approved commit per workspace rule.

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
