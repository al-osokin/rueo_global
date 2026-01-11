# rueo_global — memory-bank

## TL;DR

- Если нужно быстро понять проект: `00_Project_Overview.md`, затем `01_Initial_Task_Description.md`.
- Если нужно понять текущий прогресс/что делали: `05_Stage1_Progress_Oct16.md` + планы/таски в `tasks/` + контекст/гайды в `docs/`.

## Основные документы (ядро)

- `00_Project_Overview.md` — что это за проект, основные компоненты.
- `01_Initial_Task_Description.md` — исходная постановка задачи, контекст.
- `02_Stage1_Lift_And_Shift.md` — этап 1 (перенос/поднятие системы).
- `03_Stage2_Full_Text_Search.md` — этап 2 (поиск).
- `04_Stage3_Semantic_Parsing.md` — этап 3 (семантический разбор).
- `06_Stage1_Structure_And_UI.md` — структура/UX/организация.

## Документация и рабочие заметки

- Правила работы prod/stage и дисциплина “план → выполнение → backport”: `docs/WORKFLOW.md`
- Шаблон файла-плана: `tasks/_TEMPLATE.md`

Раньше эти файлы жили в корне репозитория, теперь они разложены здесь (чтобы агент всегда читал структурированный вариант).

- **Ориентация/контекст:** `docs/Agents.md`, `docs/Agents.ISSUE12_CONTEXT.md`
- **Архитектура/разбор:** `docs/PARSER_ARCHITECTURE_NOTES.md`
- **Гайды:** `docs/MANUAL_OVERRIDE_GUIDE.md`
- **Планы/таски:**
  - `tasks/PLAN_LEGACY_PARSER_FIX.md`
  - `tasks/PLAN_ISSUE5_MULTILINE.md`
  - `tasks/TASK_ISSUE12_V2_FOCUSED.md`
  - `tasks/TASK_ISSUE12_ILI_EXPANSION.md`
  - `tasks/TASK_LEGACY_PARSER_CONTEXT.md`
  - `tasks/TASK_UI_IMPROVEMENTS.md`

Исторические “снимки” на всякий случай оставлены в `docs/root-md-snapshots/`.

## Что бы я предложил следующим шагом (без действий пока)

1. Разобрать, что из `tasks/` актуально прямо сейчас, а что пора в архив.
2. (Опционально) упростить/объединить документы: например, свести несколько тасков в один “текущий план”.
3. Если захочешь «идеально под OpenSpec» — завести в `openspec/specs/` 2–4 базовые capability (parser, review-ui, import/pipeline, deployment) и дальше вести изменения через `openspec/changes/`.
