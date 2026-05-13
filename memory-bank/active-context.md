# Active Context — rueo.ru (prod)

Updated: 2026-05-13 15:20 (Europe/Moscow)

## Where we are
- Рабочий проект: `~/rueo_master` (prod / Stage I + dictionary update pipeline).
- Последняя текущая задача: minor frontend content/code cleanup для страницы `info.vue` и версии приложения.

## 2026-05-13 — frontend minor update prepared

Изменения в `rueo_master`:
- Список меценатов вынесен из `frontend-app/src/pages/info.vue` в редактируемый текстовый файл `frontend-app/public/mecenatoj.txt`.
  - Формат: одна непустая строка = один меценат.
  - Строки, начинающиеся с `#`, игнорируются как комментарии.
  - В список добавлены `Наталья Машкова` и `Айрат Миргалиев`.
- `info.vue` загружает `/mecenatoj.txt` через `fetch` при `mounted()`.
- В `frontend-app/src/layouts/MainLayout.vue` копирайт переведён с фиксированного `2009-2025` на динамический `2009-{{ currentYear }}`.
- Версия frontend/PWA поднята `1.0.5 → 1.0.6` в:
  - `frontend-app/package.json`
  - `frontend-app/package-lock.json`
  - `frontend-app/public/package.json`

Проверки:
- `npm run build` в `frontend-app` — успешно.
- `frontend-app/dist/spa/package.json` содержит `1.0.6`.
- `frontend-app/dist/spa/mecenatoj.txt` создаётся при сборке.

Синхронизация с Stage II:
- Та же правка перенесена в `~/rueo_global`, но там оставлена без коммита, потому что в worktree уже висят незакоммиченные разработки Stage II.

## Previous prod dictionary update
- 2026-05-08 выполнено очередное обновление словаря с последним русским словом `придерживаться`.
- Пайплайн: Dropbox sync-in → local import → sync-back → local DB dump → restore server DB → deploy `backend/data/tekstoj/{klarigo,renovigxo}.md`.
- Проверки после пайплайна:
  - `backend/data/src/last-ru-letter.txt` содержит `придерживаться`.
  - `https://rueo.ru/` отвечает HTTP 200.
  - `https://rueo.ru/search?query=придерживаться` отвечает и возвращает 1 совпадение.

## 2026-05-13 — PWA deploy automation

Создан скрипт `scripts/deploy_frontend_pwa.sh`:
- Собирает frontend командой `npx quasar build -m pwa`.
- Синхронизирует `frontend-app/dist/pwa/` в `root@rueo.ru:/var/www/slovari/data/www/rueo.ru/` через `rsync`.
- По умолчанию работает как dry-run; реальный деплой — `./scripts/deploy_frontend_pwa.sh --apply`.
- Использует `--delete`, чтобы убирать старые hashed assets и старые `manifest-*.json`.
- Защищает серверные директории от удаления:
  - `/backend/`
  - `/webstat/`
  - `/cgi-bin/`
- Выставляет владельца новых/обновлённых файлов через `--chown=slovari:slovari`.

Проверка реальным деплоем выполнена:
- `https://rueo.ru/package.json` отвечает 200 и содержит `version = 1.0.6`.
- `https://rueo.ru/mecenatoj.txt` отвечает 200.
- `https://rueo.ru/` отвечает 200.
- На сервере остался только `manifest-1.0.6.json`; старый `manifest-1.0.5.json` удалён физически.
- Protected dirs на сервере сохранены: `backend`, `webstat`, `cgi-bin`.

## Next step
- Если деплой считается успешным — закоммитить deploy script в `rueo_master`.
- Для следующих minor frontend-деплоев использовать `./scripts/deploy_frontend_pwa.sh --apply`.
