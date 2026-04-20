# Parser v4 — tasks (итерация 1)

## T1. Feature flag + wiring
- [x] Добавить выбор движка парсинга через `PARSER_ENGINE=legacy|v3|v4|hybrid`
- [x] Оставить `v3` дефолтом
- [ ] Подготовить безопасный fallback на `v3` при ошибке v4

## T2. v4 structural AST (MVP)
- [x] Новый модуль `backend/app/parsing/parser_v4/`
- [x] AST-модель: `article -> forms -> blocks`
- [x] Выделение headword/subheadwords
- [x] Выделение numbered-блоков (`1.`, `2.`)
- [ ] Сохранение offset/indent/raw_lines

## T3. Tilde expansion (MVP)
- [ ] Функция раскрытия `~` относительно главной леммы
- [x] Хранить `raw` и `expanded`
- [ ] Покрыть кейсы `~a`, `~ig/o`

## T4. Line merge deterministic rules (MVP)
- [ ] Склейка продолжений по отступу
- [ ] Нельзя ломать границы numbered-блоков
- [ ] Сохранять разделители как токены

## T5. Golden regression harness
- [x] Зафиксировать входы для id `1,2,3,6,56,77`
- [ ] Добавить snapshot AST v4
- [ ] Добавить smoke сравнение с текущим review payload

## T6. Hybrid semantic adapter (следующий шаг)
- [ ] Интерфейс `semantic_resolver.resolve(block)`
- [ ] Протокол JSON schema для LLM
- [ ] Флаги confidence / needs_human_review
