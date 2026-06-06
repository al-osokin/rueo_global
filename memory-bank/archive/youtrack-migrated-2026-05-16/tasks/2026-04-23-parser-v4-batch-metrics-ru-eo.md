# Parser v4 — батч-метрики маршрутизации review (RU↔EO)

Дата: 2026-04-23

## Цель
Зафиксировать быстрые операционные метрики для шага 2 плана:
- clean
- line-merge-risk
- many-to-many

## Воспроизводимый инструмент
Добавлен скрипт:
- `scripts/parser_v4_batch_metrics.py`

Запуск (из корня `rueo_global`):
```bash
PYTHONPATH=backend python scripts/parser_v4_batch_metrics.py --limit 300
PYTHONPATH=backend python scripts/parser_v4_batch_metrics.py --limit 1200
```

## Результаты
### Окно 1: первые 300 статей (`offset=0, limit=300`)
- clean: **163**
- line-merge-risk: **125**
- many-to-many: **12**
- errors: **0**

### Окно 2: первые 1200 статей (`offset=0, limit=1200`)
- clean: **714**
- line-merge-risk: **453**
- many-to-many: **33**
- errors: **0**

## Примечание по методике
Классификация пока эвристическая (по признакам `_или_`, комбинациям `;`/`,`/скобок, плотности разделителей), нужна для оперативного роутинга в review-v4, не как финальная научная метрика качества.

## Следующий шаг
1. Вынести эти flags в `/admin/review-v4` (видимые метки на блоке).
2. Для `many-to-many` + части `line-merge-risk` добавить роутинг в Gemma.
3. Для `clean` оставить fast-path (auto-accept candidate при достаточной confidence).
