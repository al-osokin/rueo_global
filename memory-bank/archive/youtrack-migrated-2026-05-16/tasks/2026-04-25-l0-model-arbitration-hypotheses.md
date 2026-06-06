# Task: L0 + model arbitration for ambiguous RU translation blocks

Date: 2026-04-25 (Europe/Moscow)
Owner: assistant + user review

## Why
Current L0 parser heuristics became too complex and sometimes conflict with each other.
A specific risk: hardcoded `adj, adj, adj noun` expansion in Russian can be wrong and create noisy candidates.

## Goal
Reduce unsafe heuristic expansion in L0 and move ambiguous cases to a model-guided arbitration flow.

## Proposed flow
1. **L0 conservative normalization**
   - Keep only safe deterministic operations:
     - remove italic parenthetical notes like `(_iun_)`, `(_кому-л._)`;
     - convert `_т.е._` to separator;
     - expand direct optional brackets `(x)` forms;
     - keep reference-note filtering (`_см._`, `_ср._`).
   - Avoid aggressive POS assumptions.

2. **Model structural analysis (JSON-only)**
   - Input: raw block + conservative normalized form.
   - Output: structured interpretation (segments, optional modifiers, headword binding, ambiguity flags).

3. **Hypothesis generation**
   - **H1 conservative**: no risky expansion.
   - **H2 expanded**: expansion permitted only when structure supports it.

4. **Model arbitration**
   - Model picks: `H1` / `H2` / `none`.
   - Returns: `choice`, `confidence`, `reason_short`.

5. **Decision policy**
   - High confidence + no red flags => auto-apply candidate.
   - Low confidence or `none` => manual review queue.

## Required JSON schema (draft)
```json
{
  "analysis": {
    "segments": ["..."],
    "relations": [{"type":"modifier_of","from":"...","to":"..."}],
    "ambiguity_flags": ["..."]
  },
  "hypotheses": {
    "h1": ["..."],
    "h2": ["..."]
  },
  "decision": {
    "choice": "h1|h2|none",
    "confidence": 0.0,
    "reason_short": "..."
  }
}
```

## Acceptance criteria
- For known problematic examples, pipeline can produce both H1/H2 and choose explicitly.
- No silent aggressive expansion when confidence is low.
- Manual queue volume decreases, while incorrect auto-expansions do not increase.

## First target examples
- `самопроизвольный, естественный, спонтанный аборт`
- `абортивный т.е. (при)останавливающий развитие`
- `сделать (себе) аборт`

## Notes
This task is intentionally separated from UI polishing. Focus is parser/resolve quality and scalable review load reduction.
