# Active Context — rueo_global

Updated: 2026-04-25 (Europe/Moscow)

## Update (AdminV4 stability pass, 2026-04-25 night)
- В `review-v4` отключён автопереразбор при открытии статьи: AST читается из сохранённого `parsed_payload`; добавлена явная кнопка `Переразобрать статью`.
- Добавлены сбросы:
  - `Сбросить подтверждения статьи` (article-level reset);
  - `Сбросить этот блок` + backend endpoint `POST /admin/v4/reset-block`.
- Улучшена UX карточки `Выбранный блок`:
  - убран агрессивный автоскролл страницы;
  - карточка позиционируется рядом с выбранным блоком (dynamic sticky top), без ухода в невидимую область.
- Добавлен многослойный вывод блока (верхним слоем более поздний результат, исходник ниже).
- Критичный фикс сохранения Apply после refresh:
  - причина: изменения JSON-поля `resolved_translations` могли не фиксироваться ORM;
  - решение: принудительная пометка изменения (`flag_modified`) при apply/reset block;
  - подтверждено вручную и через API-проверку: после refresh подтверждения сохраняются.
- Проверки после правок:
  - `PYTHONPATH=. pytest tests/test_admin_v4_endpoints.py -q` → 16 passed;
  - `npm run build` (frontend-app) → build succeeded.

## Update (pause/handoff, 2026-04-25)
- Зафиксирована пауза по проекту на конец недели (пользователь занят).
- Контекст сохранён без новых кодовых изменений; задача — безопасно возобновиться с текущей точки без потерь.
- Режим возврата: начать с shortlist 10 кейсов в `/admin/review-v4`, затем перенести решения в mini-regression.

## Update (AdminV4 UX+hydrate, recovered from chat)
- Добавлена автодоводка карточки `Выбранный блок`: при выборе блока выполняется `scrollIntoView` (sticky-only поведение признано неудобным при глубокой прокрутке).
- Исправлено восстановление подтверждений после refresh:
  - backend `GET /admin/v4/articles/{lang}/{art_id}/ast` теперь отдаёт `resolved_blocks`;
  - frontend в `loadAst()` гидратит `blockFlags` (`applied/dirty`) из `resolved_blocks`.
- Верификация после правок: `pytest backend/tests/test_admin_v4_endpoints.py` — 14 passed; `npm run build` — ok.
- Нюанс данных: legacy-записи в `resolved_translations.groups` без `form_id/block_id` (`None`) не маппятся к конкретным блокам в UI.
- Следующий шаг (опционально): миграционный эвристический костыль для article 77, чтобы попытаться сопоставить legacy-группы блокам и показать их в UI.

## Update (new)
- Выполнено feasibility-исследование workflow `parser_v4 + Gemma` на первых 120 статьях словаря (`artikoloj_ru`, `ORDER BY art_id LIMIT 120`).
- Результат сохранён: `memory-bank/tasks/2026-04-21-parser-v4-gemma-feasibility-first120.md`.
- Подготовлены: паттерны проблем, план L0+эскалации в Gemma, JSON-схема ответа, confidence/flags, chunking, Telegram-сценарий.
- Проверен текущий путь интеграции `/admin/v4/resolve-block`: сейчас это `gemma-assist-stub` (dry-run подтверждён, live Gemma ещё не подключена).



## Update (Gemma Assist quality, follow-up after 4b9c37b)
- В `backend/app/services/article_review.py` усилен LM Studio parser для `/admin/v4/resolve-block`:
  - поддержка `message.content` как dict / JSON-строка / массив чанков;
  - fallback на JSON-блок из `reasoning_content` (если в content валидного JSON нет);
  - reasoning в candidates больше не протекает (берём только поле `candidates` из распарсенного JSON).
- Добавлена пост-обработка candidates: нормализация пробелов/пунктуации, удаление служебных/объяснительных хвостов, фильтрация мусора, dedup (case-insensitive), limit 5.
- Добавлены тесты в `backend/tests/test_admin_v4_endpoints.py` на:
  - воспроизведение дублей/англ. explanatory leakage и их фильтрацию;
  - парсинг JSON-строки в content;
  - парсинг content-массива + fallback на JSON из reasoning.

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

## Update (hard cases set for parser_v4 EO↔RU)
- Подготовлен репрезентативный набор сложных кейсов для совместной ручной валидации:
  - файл: `memory-bank/tasks/2026-04-21-parser-v4-hard-cases-eo-ru.md`.
  - объём: 50 кейсов (25 переводов + 25 примеров).
  - есть кластеризация по паттернам (`_или_`, списки `,`/`;`, тильда `~`, пометы `_перен._/_мед._/_т.е._/_см._/_ср._`, нумерованные блоки и т.д.).
  - для каждого кейса: `article_id`, `headword`, RU/EO фрагменты, причина сложности, ожидаемая нормализация `eo|ru`, confidence.
  - отдельно выделен shortlist из 10 быстрых показательных кейсов для прохода в `/admin/review-v4`.

## Where we left off
- Feasibility + quality groundwork по `parser_v4` и `resolve-block` сделан (см. выше).
- Теперь добавлен датасет трудных кейсов для совместного разбора с пользователем и уточнения правил L0/Gemma/manual.

## Next step when resuming
1. Пройти shortlist (10 кейсов) в `/admin/review-v4` вместе с пользователем и зафиксировать фактические Accept/Edit/Reject.
2. На основе расхождений обновить механические правила (L0): `_или_`-ветвление, split по `;`/`,`, поведение `~`, фильтрация reference-note.
3. Для остатка из 50 кейсов пометить, какие блоки лучше отдавать в Gemma (ambiguous), какие — решать детерминированно.
4. После ручной валидации подготовить mini-regression набор для parser_v4 (fixtures + expected normalized pairs).


## Update (road validation session, 2026-04-21)
- Проведена оперативная ручная валидация в чате (в дороге) по сложным EO↔RU кейсам из набора `2026-04-21-parser-v4-hard-cases-eo-ru.md`.
- Подтверждены/уточнены правила:
  - `;` — надёжный разделитель значений;
  - `(_или_)` в EO/RU раскрывать в варианты;
  - прямые скобки в RU/EO раскрывать в отдельные варианты (напр. `не ахти как (хорошо)` → два варианта);
  - курсивные скобки — чаще note/preamble, не отдельный перевод;
  - `_см._/_ср._` — reference-note, не перевод;
  - при раскрытии скобок в одной стороне соответствие часто many-to-many, не index-alignment;
  - если фрагмент обрезан/грязный (`fragment-truncated`) — не автонормализовать, отложить до полного контекста.
- Зафиксированы эталоны для ключевых случаев:
  - `aborto`: `преждевременные роды | самопроизвольный аборт | естественный аборт | спонтанный аборт`;
  - `aborta`: `абортивный | недоношенный | недоразвитый | остановившийся в развитии`;
  - `abortajxo`: `недоносок | выкидыш | абортус | нежизнеспособный плод`;
  - `advokati`: `выступать в роли адвоката | выступать в роли защитника | адвокатствовать | работать адвокатом`;
  - EO list alignment: `akuta/orta/malakuta/strecxita angulo` ↔ `острый/прямой/тупой/развёрнутый угол`.
- Отложены как `unresolved`/`incomplete` кейсы с потерей хвоста/контекста (в т.ч. case 17 и case 41) для проверки у компьютера.

## Next step when resuming
1. Перенести подтверждённые эталоны в fixture/mini-regression набор parser_v4.
2. Добавить в post-processing правила для прямых скобок и EO `_или_`-ветвлений (без перераздувания шаблонов).
3. Реализовать режим many-to-many соответствия для случаев с односторонним раскрытием скобок.
4. Довести `fragment-truncated/incomplete` кейсы по полным строкам из корпуса и закрыть unresolved список.
