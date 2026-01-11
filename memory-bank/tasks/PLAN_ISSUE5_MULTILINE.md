# Plan: Issue #5/#9 - Multiline Translation Continuation

## Problem
Article 54, section `[~iĝ/i]`:
```
6: [~igx/i] ок`ончить ср`еднее уч`ебное завед`ение, пройт`и выпускн`ой
7: 	экз`амен (_в среднем учебном заведении_), пройт`и экз`амен
8: 	на аттест`ат зр`елости;
```

**Expected:** 3 complete translations
1. окончить среднее учебное заведение
2. пройти выпускной экзамен (_в среднем учебном заведении_)
3. пройти экзамен на аттестат зрелости

**Current:** 3 groups with fragments
- Group 1: `['окончить...', 'пройти выпускной']` ← cut off!
- Group 2: `['экзамен', 'пройти экзамен']` ← lost context
- Group 3: `['зрелости']` ← only last word

## Root Cause

Parser creates **separate translation blocks** for each line:
```json
{
  "type": "headword",
  "children": [
    {
      "type": "translation",
      "content": [
        {"type": "text", "text": "ок`ончить ср`еднее уч`ебное завед`ение"},
        {"type": "divider", "kind": "near_divider", "text": ","},
        {"type": "text", "text": "пройт`и выпускн`ой"}
      ]
    },
    {
      "type": "translation",  // SEPARATE BLOCK!
      "content": [
        {"type": "text", "text": "экз`амен (_в среднем учебном заведении_)"},
        ...
      ]
    }
  ]
}
```

Each continuation line becomes a **separate translation child** instead of being merged.

## Solution

Create `_merge_translation_continuations()` function (similar to existing `_merge_illustration_continuations()`).

**Location:** `/home/avo/rueo_global/backend/app/parsing/parser_v3/normalization.py`

**Insert after:** `_merge_illustration_continuations()` (around line 226)

**Call from:** `_normalize_headword()` function (around line 427)

## Implementation

### Step 1: Create merge function

```python
def _merge_translation_continuations(block: Dict[str, Any]) -> None:
    """
    Merge consecutive translation children in headword blocks.
    
    When a translation spans multiple indented lines (continuation),
    parser creates separate translation blocks. This function merges them.
    
    Example:
        Line 1: "окончить..., пройти выпускной"
        Line 2: "  экзамен, пройти экзамен"  ← continuation
        Line 3: "  на аттестат зрелости;"  ← continuation
    
    These create 3 separate translation children, but should be merged into one.
    """
    if block.get("type") != "headword":
        return
    
    children = block.get("children", []) or []
    if len(children) < 2:
        return
    
    merged_children: List[Dict[str, Any]] = []
    current_translation: Optional[Dict[str, Any]] = None
    
    for child in children:
        child_type = child.get("type")
        
        # If this is a translation block without ru_segments or children
        # it might be a continuation line
        if child_type == "translation":
            content = child.get("content", [])
            has_ru_segments = bool(child.get("ru_segments"))
            has_children = bool(child.get("children"))
            
            # Simple translation block (just content) - potential continuation
            if content and not has_ru_segments and not has_children:
                
                if current_translation is None:
                    # First translation - start accumulating
                    current_translation = dict(child)
                else:
                    # Continuation - merge content
                    current_content = current_translation.setdefault("content", [])
                    
                    # Add continuation content
                    for item in content:
                        current_content.append(item)
                
                continue
        
        # Different block type OR translation with special fields - flush current
        if current_translation is not None:
            merged_children.append(current_translation)
            current_translation = None
        
        merged_children.append(child)
    
    # Flush last accumulated translation
    if current_translation is not None:
        merged_children.append(current_translation)
    
    if merged_children:
        block["children"] = merged_children
```

### Step 2: Call from _normalize_headword()

```python
def _normalize_headword(block: Dict[str, Any]) -> Dict[str, Any]:
    new_block = dict(block)
    
    # NEW: Merge translation continuations BEFORE other processing
    _merge_translation_continuations(new_block)
    
    children = new_block.get("children") or []
    if children:
        last_child = children[-1]
        if last_child.get("type") in {"explanation", "translation"}:
            trailing = _strip_sentence_ending(last_child.get("content", []))
            if trailing:
                new_block["_trailing_sentence"] = trailing
    return new_block
```

## Testing

### Test Case 1: Article 54 [~iĝ/i]
```python
PYTHONPATH=backend python - <<'PY'
from app.database import SessionLocal, init_db
from app.services.article_review import ArticleReviewService

init_db()
with SessionLocal() as session:
    payload, _ = ArticleReviewService(session).reparse_article('eo', 54)
    
    print("=== Article 54 [~iĝ/i] after fix ===")
    for g in payload['groups']:
        if '~iĝ/i' in g.get('section', ''):
            print(f"Items: {g['items']}")
    
    # Expected: ONE group with 3 complete translations
PY
```

### Test Case 2: Regression
```python
# Article 270: should still have 25 groups
# Article 383: should still have 48 groups
```

## Expected Result
- Article 54 `[~iĝ/i]`: **1 group** with 3 complete translations instead of 3 fragmented groups
- No regressions in other articles

## Files to Modify
- `/home/avo/rueo_global/backend/app/parsing/parser_v3/normalization.py` (only file)

## Success Criteria
- [ ] Article 54 shows complete translations
- [ ] Article 270: 25 groups (no regression)
- [ ] Article 383: 48 groups (no regression)
- [ ] Code compiles without errors
