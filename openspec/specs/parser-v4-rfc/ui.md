# Parser v4 Review UI — draft mini-spec

## Context
Review flow is now **v4-only**: UI receives structured review groups from `meta.v4_ast` and must not silently fall back to legacy v3 text heuristics.

## Goals
1. Make structural verification explicit for every article.
2. Surface parser consistency problems early (missing/inconsistent `v4_ast`).
3. Add assisted editing path with **Gemma Assist** suggestions without auto-applying them.

## Non-goals
- No auto-save of AI suggestions.
- No parser-side fallback to v3 logic.

## API contract (UI-facing)
`GET /admin/articles/{lang}/{art_id}` returns:
- `success: boolean`
- `parse_error?: string`
- `review_diagnostic?: { code: string; message: string; hint: string }`
- `groups: ReviewGroup[]`
- `review_notes: string[]`

If `review_diagnostic` exists, UI must show a blocking diagnostic panel.

## Screen structure
1. **Header**
   - headword, art_id, parsing status
   - badge: `v4 review`
2. **Structural verification panel**
   - checklist:
     - forms parsed
     - sense labels detected
     - examples mapped (`eo_source` present where expected)
     - note/reference isolation (`ср./см.` are in notes, not in translation items)
3. **Groups list**
   - each group: section, label, candidate selector, manual override
   - show `eo_source` inline for example groups
4. **Gemma Assist panel**
   - input context: selected group + neighboring groups + notes
   - actions:
     - `Generate alternative`
     - `Paraphrase concise`
     - `Check terminology consistency`
   - output is editable draft, applied only by explicit user click

## Blocking diagnostics UX
When `review_diagnostic` is present:
- hide/disable review controls
- render panel:
  - title: "Parser v4 diagnostic"
  - message from `review_diagnostic.message`
  - hint from `review_diagnostic.hint`
  - CTA: `Reparse article` (calls `/admin/articles/{lang}/{art_id}/reparse`)

## Gemma Assist interaction model
- Trigger modes:
  - per-group inline button
  - right-side panel with current group context
- Safety:
  - never overwrite accepted/manual values automatically

### Backend API (implemented)

#### `POST /admin/v4/resolve-block`
Draft generator (stub-провайдер, без реального LLM вызова).

Request:
```json
{
  "article_id": 77,
  "lang": "eo",
  "form_id": "form_0",
  "block_id": "block_1",
  "context": {
    "label": "пример beta",
    "items": ["бета"],
    "base_items": ["бета"],
    "eo_source": "beta",
    "review_notes": []
  }
}
```

Response:
```json
{
  "provider": "gemma-assist-stub",
  "candidates": ["бета", "бета (уточнить)"],
  "confidence": 0.42,
  "rationale_short": "Stub provider: черновые варианты сформированы локально без вызова модели."
}
```

Validation:
- `article_id >= 1`
- `lang` обязателен (`eo|ru`)
- `form_id`, `block_id` — непустые строки

#### `POST /admin/v4/apply-resolution`
Сохраняет операторское решение в `article_parse_state.resolved_translations.groups[*].operator_action`.

Request:
```json
{
  "article_id": 77,
  "lang": "eo",
  "form_id": "form_0",
  "block_id": "block_1",
  "operator_action": {
    "action": "edit",
    "selected_candidate_id": "c2",
    "value": "бета",
    "comment": "уточнил форму"
  }
}
```

Response:
```json
{
  "status": "ok",
  "article_id": 77,
  "lang": "eo",
  "form_id": "form_0",
  "block_id": "block_1",
  "operator_action": {
    "action": "edit",
    "selected_candidate_id": "c2",
    "value": "бета",
    "comment": "уточнил форму"
  }
}
```

Validation:
- `operator_action.action` ∈ `accept|edit|reject`
- все идентификаторы и `lang` обязательны

## Acceptance criteria (draft)
1. If `v4_ast` missing or invalid, user sees blocking diagnostic within 1 render cycle.
2. No translation groups are shown from legacy fallback when diagnostic is present.
3. Reviewer can inspect structural checklist before editing groups.
4. Gemma suggestions are visible, diffable, and manually applied.
5. Saving review preserves current candidate/manual behavior unchanged.

## Open questions
- Should Gemma run server-side or directly via frontend gateway?
- Do we need per-group confidence scoring in API?
- Should checklist include parser version/hash for traceability?


### UX замечание (из текущего прогона)
- Для примеров в интерфейсе показывать заголовок в формате: `пример <EO>` (например, `пример beta`),
  а перевод — отдельной строкой/блоком (`бета`).
- Не использовать section/headword (например, `[-a II]`) как заголовок примера — это визуально маскирует тип узла.
