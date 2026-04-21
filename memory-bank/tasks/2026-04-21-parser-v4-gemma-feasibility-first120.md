# Feasibility research: parser_v4 + Gemma on first dictionary entries

Date: 2026-04-21 (Europe/Moscow)
Scope: `/home/avo/rueo_global`, first 120 entries from `artikoloj_ru` (ordered by `art_id`).

## 1) Dataset and run method

- Sample source: PostgreSQL table `artikoloj_ru`.
- Selection: `ORDER BY art_id LIMIT 120`.
- Parser tested: `backend/app/parsing/parser_v4/pipeline.py` (`ParsingPipelineV4`).
- Why this source: first entries are available in DB in clean encoding and represent real production articles.

## 2) Pattern findings on first 120 entries

Observed counts (block-level):

- `parentheses`: **108**
- `comma + semicolon in same block`: **73**
- `adj+noun enumeration` (heuristic): **28**
- `mixed verbal/nominal rows` (heuristic): **19**
- `or/aux/или markers`: **8**
- Abbreviation hits in this slice: **0 explicit** for `т.е./и т.д./...` by regex (but abbreviation handling still needed globally).

### Typical problematic patterns (representative)

1. **Numbered sense starts with explanatory parenthetical note**
2. **Mixed RU+EO examples with both commas and semicolons**
3. **`или / aux` alternation semantics**
4. **Adjective+noun bundled items**
5. **Mixed verb+noun row**

## 3) Gemma prompt variants + local tests

Current `resolve-block` path (`POST /admin/v4/resolve-block` -> `ArticleReviewService.resolve_block_draft`) uses **stub provider**:

```json
{
  "provider": "gemma-assist-stub",
  "confidence": 0.42
}
```

No live Gemma call yet. Feasibility was tested via dry-run through existing resolve-block contract.

### Prompt variants (proposed)

- **V1 strict normalization** — canonical translations only.
- **V2 typed semantic split** — `kind: nominal|verbal|phrase|note`.
- **V3 punctuation-aware conservative** — `;` stronger than `,`, notes separated.
- **V4 alternative-aware** — explicit `или/aux` conditional alternatives.

Dry-run status: 6 representative contexts processed, provider always `gemma-assist-stub`, confidence 0.42, candidates generated from context items.

## 4) Context limits and block-level chunking proposal

Empirical stats (first 120):

- Article char length: p50 **42.5**, p90 **220**, max **5431**
- Blocks/article: p50 **1**, p90 **4**, max **74**
- Block raw length: p50 **31**, p90 **85**, p99 **184**, max **679**

### Proposed chunking

- Primary chunk = one target block.
- Left/right context = up to 2 sibling blocks each side.
- Caps:
  - `target_block_chars <= 450`
  - `total_context_chars <= 1200`
  - `max_blocks_in_prompt <= 7`
- Oversize split: first by top-level `;`, then by commas outside parentheses, with `split_trace` metadata.

## 5) Concrete implementation plan

### L0 safe deterministic mechanics

- normalize + whitespace cleanup
- isolate parenthetical notes
- classify punctuation boundaries
- detect reference markers (`см./ср.`)
- detect `или/aux` alternatives
- if high-confidence deterministic result exists, skip model

### Escalation to Gemma

Escalate if one or more:
- mixed verbal+nominal signals
- nested punctuation ambiguity (`;` + `,` + parentheses)
- alternatives/conditions markers (`или/aux`) with >1 grouping
- repeated operator reject/edit on similar fingerprint
- L0 confidence `<0.72`

### JSON schema (proposal)

```json
{
  "provider": "gemma",
  "model": "gemma-2-9b-it",
  "decision": "accept|needs_review|abstain",
  "confidence": 0.0,
  "items": [
    {
      "text": "...",
      "kind": "nominal|verbal|phrase|note|alternative",
      "source_span": [0, 0],
      "flags": ["comma_semicolon", "parenthetical_note"]
    }
  ],
  "notes": ["..."],
  "alternatives": [{"condition": "...", "items": ["..."]}],
  "safety": {"hallucination_risk": "low|medium|high", "format_ok": true}
}
```

### Confidence/flags

- final confidence blend = L0 structure (40%) + model score (20%) + validator/schema score (40%)
- key flags: `comma_semicolon`, `parenthetical_note`, `contains_or_marker`, `mixed_pos`, `requires_operator_review`

### Operator feedback loop

- store fingerprint + model output + operator action + edit text
- weekly: harvest hard negatives from reject/edit, update L0 rules + prompt exemplars

## 6) Telegram-friendly short daily flow

1. “Нашёл 24 неоднозначных блока. Показать по 5?”
2. User confirms.
3. For each block: short context + 2–3 candidates + buttons ✅/✏️/❌.
4. Batch summary: accepted/edited/rejected.
5. End-of-day: auto-accept %, Gemma escalation %, manual %.

## 7) Risks

- Real Gemma quality not yet measured (stub only).
- First-120 slice is skewed by long service/conjunction entries.
- Heuristic detectors need calibration on labeled set.
- ORM/services expect `article*` naming while actual DB uses `artikoloj*` (integration risk).

## 8) Commands/checks executed

```bash
ls -la /home/avo/rueo_global
python3 - <<'PY'  # list public tables
...
PY
python3 - <<'PY'  # inspect artikoloj/artikoloj_ru schema and counts
...
PY
python3 - <<'PY'  # parse first 120 + pattern counters
# output: /tmp/parser_v4_first120_ru_summary.json
...
PY
PYTHONPATH=/home/avo/rueo_global/backend python3 - <<'PY'  # resolve-block dry-run
# output: /tmp/parser_v4_context_dryrun.json
...
PY
```
