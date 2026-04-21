# Active Context — rueo_global

Updated: 2026-04-21 (Europe/Moscow)

## Update (new)
- Выполнено feasibility-исследование workflow `parser_v4 + Gemma` на первых 120 статьях словаря (`artikoloj_ru`, `ORDER BY art_id LIMIT 120`).
- Результат сохранён: `memory-bank/tasks/2026-04-21-parser-v4-gemma-feasibility-first120.md`.
- Подготовлены: паттерны проблем, план L0+эскалации в Gemma, JSON-схема ответа, confidence/flags, chunking, Telegram-сценарий.
- Проверен текущий путь интеграции `/admin/v4/resolve-block`: сейчас это `gemma-assist-stub` (dry-run подтверждён, live Gemma ещё не подключена).


## Where we left off
- Восстановлен контекст после аварии сессии/сброса контекста.
- По словам из последнего рабочего отчёта (до поломки):
  1. **Parser fix (backend, parser_v4)**
     - Цель: `_см._` / `_ср._` классифицировать только как reference/note, никогда не как sense.
     - Изменён `backend/app/parsing/parser_v4/pipeline.py`:
       - добавлен helper `_is_reference_note(...)`;
       - в `_append_block(...)` для нумерованных строк ссылочные строки идут в `type="note"`.
     - Кейс id77 `abortulo 1`: `1. _см._ ~ajxo;` должен быть `note`, не `sense`.
  2. **Тесты parser_v4**
     - Добавлен регрессионный тест в `backend/tests/test_parser_v4_merge.py`:
       - `test_id77_abortulo_first_numbered_reference_is_note_not_sense`.
     - Обновлён snapshot: `backend/tests/fixtures/parser_v4_golden.json`.
  3. **Frontend /admin/review-v4 actionability**
     - В `frontend-app/src/pages/AdminV4Review.vue` добавлены действия по выбранному блоку:
       - `Accept / Reject / Edit`;
       - для `Edit` — поле ввода;
       - отправка в `POST /admin/v4/apply-resolution`;
       - визуальная метка `applied` после успешного применения.

## Verification reported previously
- Backend tests (пакет parser/admin): **22 passed**.
- Frontend build: **build succeeded**.
- Коммит не делался.

## Current blocker / trust context
- Была проблема дисциплины исполнения в агенте: статусы без реального запуска действия.
- Договорённость с пользователем (Саша):
  - сначала реальный запуск процесса/субагента,
  - потом статус с явным указанием, что именно запущено (и id, когда применимо).

## Next step when resuming
1. Подключить реальный Gemma provider вместо `gemma-assist-stub` в `ArticleReviewService.resolve_block_draft` (через отдельный adapter/endpoint с timeout+retry).
2. Реализовать L0 pre-normalization + chunking policy из отчёта (`target<=450 chars`, `context<=1200`, `<=7 blocks`).
3. Ввести JSON-schema validator ответа модели и единый расчёт confidence/flags.
4. Прогнать второй срез (например, статьи 1000-1120) для проверки смещения паттернов относительно первых 120.
5. Подготовить минимальный UI/Telegram контур operator-feedback (accept/edit/reject -> сохранение для weekly hard-negatives).
