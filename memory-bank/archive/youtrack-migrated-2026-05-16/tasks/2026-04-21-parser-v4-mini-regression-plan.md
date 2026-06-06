# Parser v4 mini-regression plan (draft)

Дата: 2026-04-21

Основано на подтверждённых кейсах из shortlist-validation-log.

## merge
- [x] [без]
- [x] [бог]
- [x] [а I]
- [x] [адрес]
- [x] line-merge
- [x] merge-fix

## brackets
- [x] (с)делать
- [x] орангутан(г)
- [x] анализ (крови)
- [x] _или_

## labels_notes
- [x] _эк._
- [ ] _см._
- [ ] _ср._
- [x] курсивные скобки

## Next executable step
- [x] Сформирован fixture `backend/tests/fixtures/parser_v4_mini_regression.json` (8 кейсов).
- [x] Добавлен тест `backend/tests/test_parser_v4_mini_regression.py` (compare only expected semantic keys).
- [x] Прогон: `PYTHONPATH=backend pytest -q backend/tests/test_parser_v4_mini_regression.py` → `2 passed`.

## Update 2026-04-23
- Закрыт первый рабочий шаг mini-regression: fixture + тест + зелёный прогон целевого теста.
- Отдельный прогон `test_parser_v4_snapshot_smoke.py` показывает 1 несовпадение снапшота (не в новом тесте); требует отдельного разбора и, вероятно, обновления golden-файла/ожиданий.

- [x] Батч-метрики RU→EO (эвристический роутинг): первые 300 и 1200 статей, см. `memory-bank/tasks/2026-04-23-parser-v4-batch-metrics-ru-eo.md`.

- [x] UI flags в `/admin/review-v4`: для блока отображается `clean` / `line-merge-risk` / `many-to-many` (эвристика как в batch metrics).
