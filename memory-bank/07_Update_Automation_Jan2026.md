# Автоматизация выгрузки Rueo (январь 2026)

Дата: 2026-01-10

## Цель

Свести регулярную процедуру обновления словаря к одному воспроизводимому пайплайну:

1) синхронизировать исходники из Dropbox → локальный `backend/data/src`
2) запустить импорт (обновить PostgreSQL и сформировать `backend/data/tekstoj/*.md`)
3) синхронизировать обратно в Dropbox файлы, которые импортёр мог автоправить (автодаты в `VortaroRE-daily`)
4) перенести готовую базу на сервер через дамп/restore (без повторного импорта на сервере)
5) выложить `klarigo.md` и `renovigxo.md` на сервер

Ключевая идея: на сервере не нужен второй прогон импортёра; достаточно переносить готовую БД и служебные файлы в `tekstoj/`.

## Скрипт обновления

Файл: `/home/avo/rueo_master/scripts/rueo_update.sh`

### Команды

- `./scripts/rueo_update.sh run --last-ru-letter <слово>`
  - полный пайплайн: `sync-in` → `import-local` → `sync-back` → `dump-local-db` → `restore-server-db` → `deploy-tekstoj`
- `./scripts/rueo_update.sh sync-in`
  - `rsync` из Dropbox:
    - `/mnt/f/Backup/Dropbox/VortaroRE-daily` → `backend/data/src/VortaroRE-daily`
    - `/mnt/f/Backup/Dropbox/VortaroER-daily` → `backend/data/src/VortaroER-daily`
  - чистка артефактов `*:com.dropbox.attrs` (на практике `rsync` их не создаёт; защита на случай копирования из Windows)
  - нормализация прав: директории `755`, файлы `644`
- `./scripts/rueo_update.sh sync-back`
  - обратный `rsync` обработанных файлов из `backend/data/src/Vortaro{RE,ER}-daily` в Dropbox
  - оставлены исключения `*:com.dropbox.attrs` / `*.attrs` как страховка
- `./scripts/rueo_update.sh import-local --last-ru-letter <слово>`
  - запуск импортёра: `python3 -m app.importer --data-dir backend/data/src --last-ru-letter <слово>`
  - если `--last-ru-letter` не указан в `run`, скрипт спрашивает интерактивно; Enter подставляет текущее значение из `backend/data/src/last-ru-letter.txt`
- `./scripts/rueo_update.sh dump-local-db`
  - создаёт дамп БД формата `pg_dump -F c` через локальный контейнер Postgres 13 `rueo_postgres`
  - путь дампа: `backend/tmp/rueo_db_<UTC>.dump`
  - `DATABASE_URL` берётся так:
    1) из env `DATABASE_URL`, если задан
    2) иначе из `docker exec rueo_backend printenv DATABASE_URL`
    3) иначе default `postgresql://rueo_user:rueo_password@localhost:5432/rueo_db`
- `./scripts/rueo_update.sh restore-server-db <dumpfile>`
  - загружает дамп на сервер: `root@rueo.ru:/root/rueo_db.dump`
  - читает `DATABASE_URL` на сервере из контейнера `rueo-backend-1` (там пароль содержит `?`, для этого сделан tolerant-парсер URL)
  - выполняет restore в контейнере Postgres на сервере `rueo-db-1`:
    - завершает активные коннекты к целевой БД
    - `pg_restore --clean --if-exists --no-owner --no-privileges`
- `./scripts/rueo_update.sh deploy-tekstoj`
  - копирует на сервер:
    - `backend/data/tekstoj/klarigo.md`
    - `backend/data/tekstoj/renovigxo.md`
  - целевой путь: `/var/www/slovari/data/www/rueo.ru/backend/data/tekstoj/`
- `./scripts/rueo_update.sh reset-tracking`
  - аварийная команда: сбрасывает трекинг изменений статей в локальной БД:
    - `TRUNCATE article_change_log, article_states, article_file_states RESTART IDENTITY CASCADE;`

### Важные переменные окружения

Скрипт поддерживает переопределения через env:

- `DROPBOX_VORTARO_RE`, `DROPBOX_VORTARO_ER`
- `NORMALIZE_PERMS=0` — отключить chmod
- `IMPORT_CMD` — если импортёр нужно запускать иначе (venv и т.п.)
- `DATABASE_URL` — локальная БД
- `LOCAL_PG_CONTAINER` (default `rueo_postgres`)
- `LOCAL_BACKEND_CONTAINER` (default `rueo_backend`)
- `SERVER_SSH` (default `root@rueo.ru`)
- `SERVER_TEKSTOJ_DIR` (default `/var/www/slovari/data/www/rueo.ru/backend/data/tekstoj`)
- `SERVER_PG_CONTAINER` (default `rueo-db-1`)
- `SERVER_BACKEND_CONTAINER` (default `rueo-backend-1`)

## Фиксация даты импорта для трекинга

Был нужен режим «восстановить baseline трекинга по прошлому обновлению», чтобы сравнение изменений работало корректно.

Изменения в коде: `/home/avo/rueo_master/backend/app/importer.py`

- Добавлен параметр CLI `--run-at` и поддержка env `RUEO_IMPORT_RUN_AT`.
- `run_import(..., run_at=...)` использует это время как `run_time` для `ArticleTracker`.

Пример baseline-прогона (для обновления 06.01.2026):

```bash
cd /home/avo/rueo_master
./scripts/rueo_update.sh reset-tracking

cd /home/avo/rueo_master/backend
PYTHONPATH=../backend RUEO_IMPORT_RUN_AT='2026-01-06' \
  python3 -m app.importer --data-dir ./data/src --last-ru-letter 'предсмертный'
```

После этого обычный прогон по актуальным файлам начинает корректно находить изменения и автодатить статьи.

## Наблюдения

- Артефакты `*:com.dropbox.attrs` характерны для копирования средствами Windows/Explorer; `rsync` между `/mnt/f/...` и Linux-папкой, судя по проверке, их не создаёт.
- Импортёр может переписывать файлы в `backend/data/src/VortaroRE-daily/*.txt` (автодаты) — поэтому важно синхронизировать эти изменения обратно в Dropbox (иначе следующий `sync-in` откатит правки).
- Для проверки того, что автодаты сработали, смотрим `backend/data/tekstoj/tracking-summary.json`:
  - поля `articles_changed`, `articles_auto_dated`, `articles_new` по `ru/eo`.

## Типовой запуск

```bash
cd /home/avo/rueo_master
./scripts/rueo_update.sh run --last-ru-letter 'предсмертный'
```

(Если `--last-ru-letter` не указан — скрипт спросит и подставит текущее значение из `backend/data/src/last-ru-letter.txt` по Enter.)
