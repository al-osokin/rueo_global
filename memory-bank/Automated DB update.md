# Automated DB update (Rueo)

Короткая шпаргалка: как обновлять базу Rueo и выгружать на сервер.

## Обычное обновление

```bash
cd /home/avo/rueo_master
./scripts/rueo_update.sh run --last-ru-letter 'предсмертный'
```

Если `--last-ru-letter` не указан, скрипт спросит интерактивно; Enter подставляет текущее значение из `backend/data/src/last-ru-letter.txt`.

## Что делает `run`

1) `sync-in`: Dropbox → `backend/data/src/{VortaroRE-daily,VortaroER-daily}` (rsync, чистка возможных `*:com.dropbox.attrs`, нормализация прав: директории 755, файлы 644)
2) `import-local`: `python3 -m app.importer --data-dir backend/data/src --last-ru-letter ...`
3) `sync-back`: `backend/data/src/Vortaro{RE,ER}-daily` → Dropbox (чтобы автодаты/правки импортёра не откатились при следующем sync-in)
4) `dump-local-db`: дамп БД через локальный контейнер Postgres 13 `rueo_postgres` (формат `pg_dump -F c`)
5) `restore-server-db`: upload дампа на `root@rueo.ru` и restore в контейнер Postgres `rueo-db-1` (с завершением активных сессий)
6) `deploy-tekstoj`: копирование `backend/data/tekstoj/{klarigo,renovigxo}.md` на сервер в `/var/www/slovari/data/www/rueo.ru/backend/data/tekstoj/`

## Полезные команды по отдельности

- `./scripts/rueo_update.sh sync-in`
- `./scripts/rueo_update.sh import-local --last-ru-letter '...'
- `./scripts/rueo_update.sh sync-back`
- `./scripts/rueo_update.sh dump-local-db`
- `./scripts/rueo_update.sh restore-server-db ./tmp/<dump>.dump`
- `./scripts/rueo_update.sh deploy-tekstoj`

## Проверка, что автодаты/трекинг сработали

Смотреть файл:
- `backend/data/tekstoj/tracking-summary.json`

Поля:
- `articles_changed`
- `articles_auto_dated`
- `articles_new`

## Аварийно: восстановить baseline трекинга “как в прошлое обновление”

Иногда нужно, если трекинг потерялся или файлы были перезатёрты.

```bash
cd /home/avo/rueo_master
./scripts/rueo_update.sh reset-tracking

cd /home/avo/rueo_master/backend
PYTHONPATH=../backend RUEO_IMPORT_RUN_AT='2026-01-06' \
  python3 -m app.importer --data-dir ./data/src --last-ru-letter 'предсмертный'
```

После этого можно делать обычный `run` по актуальным файлам.
