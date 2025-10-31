# FOCUSED: Issue #1 - Grave Accent Word Merging

## CRITICAL BUG - HIGHEST PRIORITY

**Problem:** `(\`имя) прилаг\`ательное` → `\`имяприлаг\`ательное` (space lost between words)

**Expected:** `прилагательное | \`имя прилагательное` (WITH space)

**Status:** Partially investigated, root cause still elusive

---

## Quick Project Context

**Stack:** FastAPI backend, PostgreSQL, parser_v3 + translation_review pipeline

**Key files:**
- `backend/app/services/translation_review.py` - Translation extraction and grouping
- `backend/app/parsing/parser_v3/text_parser.py` - Text parsing (already uses character-by-character, not regex)

**Data flow:**
1. Parser → structured JSON with text nodes
2. `_split_translation_groups()` → processes text nodes into base/expanded
3. `_expand_parenthetical_forms()` → expands `(optional)` parts
4. Various normalization → `_clean_spacing()`, `_normalize_compound_terms()`
5. Final items → appear in UI

---

## Issue #1 Details

### Test Article
**Article 2** (a-vort/o), line in source:
```
[a-vort/o] (_только в эсперанто_) (`имя) прилаг`ательное
```

### Current Behavior
```python
# Group items show:
['прилаг`ательное', '`имяприлаг`ательное']
#                     ^^^^ NO SPACE HERE ^^^^
```

### Expected Behavior
```python
['прилагательное', '`имя прилагательное']
#                   ^^^ WITH SPACE ^^^
```

### Investigation Results (from previous session)

**✓ Confirmed working:**
1. `_expand_parenthetical_forms("(\`имя) прилаг\`ательное")` returns:
   ```python
   ['прилаг`ательное', '`имя прилаг`ательное']  # WITH SPACE!
   ```

2. `_clean_spacing()` preserves the space:
   ```python
   _clean_spacing('`имя прилаг`ательное')  # → '`имя прилаг`ательное'
   ```

3. `_normalize_compound_terms()` preserves the space:
   ```python
   _normalize_compound_terms(['`имя прилаг`ательное'])  # → ['`имя прилаг`ательное']
   ```

**❌ Problem occurs somewhere AFTER these functions!**

Space is lost in some intermediate step between expansion and final group items.

### Key Functions to Investigate

**Pipeline in `_split_translation_groups()` (lines ~820-860):**
```python
for base in base_groups:
    # Line 830: Expand parentheses
    expanded.extend(
        variant
        for variant in _expand_parenthetical_forms(item)
        if variant
    )
    # Line 836: Strip punctuation
    expanded = _deduplicate([_strip_trailing_punctuation(x) for x in expanded])
    # Line 837: Filter meaningful
    expanded = [item for item in expanded if _is_meaningful_item(item)]
    # Line 838: Cross product expansion
    expanded = _expand_cross_product(expanded)
    # Line 839: Suffix appending
    expanded = _expand_suffix_appending(expanded)
    # Line 840: Final deduplicate
    expanded = _deduplicate(expanded)
```

**Suspects:**
1. `_expand_cross_product()` - manipulates phrases with spaces
2. `_expand_suffix_appending()` - might concatenate without spaces
3. `_deduplicate()` - shouldn't affect spaces, but check
4. Something in `_collect_groups_from_blocks()` after spec creation

### Recent Fixes (Completed)
- Issue #13: Official marks filtering ✓
- Issue #8: Reference filtering ✓
- Issue #7: "Как в источнике" candidate ✓
- Issue #10: Empty groups ✓
- Issue #4: Tilde examples ✓
- Issue #6: Parentheses preservation (partial) ✓

---

## CLI Debugging Helpers

### Test expansion directly
```bash
PYTHONPATH=backend python - <<'PY'
from app.services.translation_review import _expand_parenthetical_forms

test = "(\`имя) прилаг\`ательное"
result = _expand_parenthetical_forms(test)
print(f"Expanded: {result}")
for item in result:
    print(f"  '{item}' (len={len(item)})")
PY
```

### Test full pipeline step-by-step
```bash
PYTHONPATH=backend python - <<'PY'
from app.services.translation_review import (
    _expand_parenthetical_forms,
    _clean_spacing,
    _normalize_compound_terms,
    _expand_cross_product,
    _expand_suffix_appending,
    _deduplicate
)

test = "(\`имя) прилаг\`ательное"

# Step by step
items = _expand_parenthetical_forms(test)
print(f"1. After expansion: {items}")

items = [_clean_spacing(x) for x in items]
print(f"2. After clean_spacing: {items}")

items = _normalize_compound_terms(items)
print(f"3. After normalize: {items}")

items = _expand_cross_product(items)
print(f"4. After cross_product: {items}")

items = _expand_suffix_appending(items)
print(f"5. After suffix_append: {items}")

items = _deduplicate(items)
print(f"6. After deduplicate: {items}")
PY
```

### Check article 2 current state
```bash
PYTHONPATH=backend python - <<'PY'
from app.database import SessionLocal, init_db
from app.services.article_review import ArticleReviewService

init_db()
with SessionLocal() as session:
    data = ArticleReviewService(session).load_article('eo', 2)
    
    for g in data['groups']:
        items = g['items']
        if any('`имя' in item or ('прилаг' in item and '`имя' in ' '.join(items)) for item in items):
            print(f"Section: {g.get('section')}")
            print(f"Items: {items}")
            print(f"Base items: {g.get('base_items')}")
PY
```

### Reparse article after changes
```bash
PYTHONPATH=backend python - <<'PY'
from app.database import SessionLocal, init_db
from app.services.article_review import ArticleReviewService

init_db()
with SessionLocal() as session:
    payload, result = ArticleReviewService(session).reparse_article('eo', 2)
    print(f"✓ Reparsed {result.headword}, groups: {len(payload['groups'])}")
PY
```

### Check parsed structure
```bash
PYTHONPATH=backend python - <<'PY'
from app.database import SessionLocal, init_db
from app.services.article_parser import ArticleParserService
import json

init_db()
with SessionLocal() as session:
    parser = ArticleParserService(session)
    result = parser.parse_article_by_id('eo', 2, include_raw=True)
    
    # Look for the problematic text
    body = result.raw.get('body', [])
    for section in body:
        if section.get('type') == 'translation':
            content = section.get('content', [])
            for node in content:
                if node.get('type') == 'text':
                    text = node.get('text', '')
                    if '`имя' in text:
                        print(f"Found text node: {repr(text)}")
PY
```

---

## Function Reference

### _expand_cross_product (line 2281)
Takes items with spaces and attempts to create combinations:
- `["word1 suffix", "word2 suffix"]` → might expand to various combinations
- **Risk:** Could concatenate without preserving spaces

### _expand_suffix_appending (need to locate)
Appends suffixes to items - **could be culprit if it doesn't add space**

### _deduplicate (simple set-based, shouldn't affect spaces)
```python
def _deduplicate(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
```

---

## Debugging Strategy

1. **Add temporary DEBUG output** at each step in `_split_translation_groups()`
   ```python
   import sys
   print(f"DEBUG after expansion: {expanded}", file=sys.stderr)
   ```

2. **Test with minimal case:**
   - Create test content with just this text node
   - Run through `_split_translation_groups()` directly
   - See where space disappears

3. **Check `_expand_cross_product` and `_expand_suffix_appending`:**
   - Test them with `['прилаг\`ательное', '\`имя прилаг\`ательное']` input
   - See if they preserve spaces

4. **Binary search through pipeline:**
   - Add asserts to check space preservation after each step
   - Find exact line where space is lost

---

## Success Criteria

✓ Article 2 `[a-vort/o]` shows: `['прилагательное', '`имя прилагательное']` WITH space

✓ No regressions in test articles:
- Article 270: 25 groups
- Article 383: 48 groups

---

## Notes

- This is HIGHEST PRIORITY issue from original 13
- Affects many articles with grave accents in optional parts
- Previous session spent significant time but didn't locate exact bug
- Space is preserved through expansion/normalization but lost somewhere after
- Likely in one of: cross_product, suffix_appending, or group building logic
