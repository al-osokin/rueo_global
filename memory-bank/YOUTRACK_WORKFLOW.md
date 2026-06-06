# YouTrack workflow — rueo.ru / Словари

Updated: 2026-05-16 (Europe/Moscow)

## Source of truth

YouTrack project `eoru` / **Словари** is the primary and determining task contour for `rueo_master` and `rueo_global`.

Project memory remains useful for handoff, research notes, implementation logs, and recovery context, but it must not become an independent backlog. If a note implies executable work, create or update a YouTrack issue and link/reference that issue from memory.

## Default rule for development tasks

Do **not** rely on project defaults for assistant-created development tasks, because defaults are used to mark incoming email/user-feedback items.

For development work created by the assistant, set fields explicitly:

- `Type`: `Задание` / `Task`
- `State`: `Открыта` / `Open`
- `Subsystem`:
  - `Движок` for current prod / Stage I / `rueo_master` engine work;
  - `Движок ST II` for Stage II / `rueo_global` work;
  - `Инфраструктура` for tracker/mailbox/Reformal import, cleanup helpers, and task-processing automation.

For clarity, Stage I issues may include `[ST I]` in the title, but the subsystem remains `Движок`.

Dictionary/mailbox/user-feedback tasks keep the existing default workflow and should not be silently reclassified unless Sasha explicitly asks.

## Creation / update discipline

Before creating a new issue:
1. Search YouTrack for a likely duplicate in `eoru`.
2. If an issue exists, update/comment/reference it instead of creating a new one.
3. If the work comes from a memory note, include the source file path and short context in the issue description.

When work starts or changes materially:
- update the YouTrack issue first (state/comment/description as appropriate);
- then update memory handoff only with a compact pointer to the current YouTrack issue(s).

When work is done:
- move to `Исправлена` only after the code/data/source change is actually made;
- move to `Проверена` only after the live site or agreed verification target is checked.

## Current migration batch

Initial assistant-created issues from project memory are listed in `memory-bank/active-context.md` after the 2026-05-16 migration pass.
