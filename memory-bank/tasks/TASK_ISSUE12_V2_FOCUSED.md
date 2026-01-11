# Task: Issue #12 - Fix `_или_` Alternative Expansion (v2)

## Problem Statement

**Article 57** has broken expansion of alternatives with `_или_` (or):

**Source text:**
```
отложительный (_или_ отделительный, _или_ исходный) падеж, аблатив
```

**Current (BROKEN):**
- 2 broken groups with unclosed parentheses and fragments

**Expected:**
- 1 group with 4 items: 
  - `отложительный падеж`
  - `отделительный падеж`
  - `исходный падеж`
  - `аблатив`

## Root Cause Analysis (ALREADY DONE)

Parser creates these nodes:
1. TEXT: `"отложительный "` ← first variant
2. NOTE: `"_или_ отделительный, _или_ исходный"` ← alternatives in parentheses
3. TEXT: `" падеж"`

Function `_extract_note_alternatives()` (line ~2007) extracts `['отделительный', 'исходный']` from the NOTE.

**The bug:** `_PhraseBuilder.add_alternatives()` adds only alternatives from NOTE, but **forgets the first variant** `"отложительный"` that was added BEFORE the note!

## Solution (Crystal Clear)

**File:** `/home/avo/rueo_global/backend/app/services/translation_review.py`

**Location:** `_PhraseBuilder` class, method `add_alternatives()` around line ~1890

**Current code (broken):**
```python
def add_alternatives(self, options: Sequence[str]) -> None:
    """Adds alternatives from note"""
    if not options:
        return
    self.components.append(list(options))
```

**Fixed code:**
```python
def add_alternatives(self, options: Sequence[str]) -> None:
    """
    Adds alternatives from note (_или_ pattern).
    
    CRITICAL: If last component has a word, that word is the FIRST variant
    that these alternatives replace. Include it in the alternatives list.
    
    Example:
        Before: components = [['отложительный']]
        Call: add_alternatives(['отделительный', 'исходный'])
        After: components = [['отложительный', 'отделительный', 'исходный']]
    """
    if not options:
        return
    
    alternatives = list(options)
    
    # Check if we have a word BEFORE the note (last component, last word)
    if self.components and self.components[-1]:
        last_component = self.components[-1]
        
        # Last component should have one option (the word before note)
        if last_component and len(last_component) == 1:
            first_variant = last_component[0].strip()
            
            # Extract last word (token) from first variant
            tokens = first_variant.split()
            if tokens:
                last_word = tokens[-1]
                remaining = ' '.join(tokens[:-1]).strip()
                
                # Add last word as FIRST alternative
                alternatives.insert(0, last_word)
                
                # Update last component with remaining text (if any)
                if remaining:
                    self.components[-1] = [remaining]
                else:
                    # No text left, remove component
                    self.components.pop()
    
    # Add all alternatives as new component
    self.components.append(alternatives)
```

## Test Instructions

### Test 1: Primary test case (Article 57)
```bash
PYTHONPATH=backend python - <<'PY'
from app.database import SessionLocal, init_db
from app.services.article_review import ArticleReviewService

init_db()
with SessionLocal() as session:
    payload, _ = ArticleReviewService(session).reparse_article('eo', 57)
    
    print("=== Article 57 [ablativ|o] ===")
    for g in payload['groups']:
        section = g.get('section', '')
        if 'ablativ' in section.lower():
            items = g['items']
            print(f"Items ({len(items)}):")
            for idx, item in enumerate(items, 1):
                print(f"  {idx}. {item}")
            
            print(f"\n✓ CHECKS:")
            print(f"  - Count: {len(items)} == 4")
            print(f"  - Contains 'отложительный падеж': {'отлож' in str(items) and 'падеж' in str(items)}")
            print(f"  - Contains 'отделительный падеж': {'отдел' in str(items) and 'падеж' in str(items)}")
            print(f"  - Contains 'исходный падеж': {'исх' in str(items) and 'падеж' in str(items)}")
            print(f"  - Contains 'аблатив': {'аблат' in str(items)}")
            print(f"  - No unclosed parens: {'(' not in ''.join(items) or ')' in ''.join(items)}")
PY
```

**Expected output:**
```
Items (4):
  1. отложительный падеж
  2. отделительный падеж
  3. исходный падеж
  4. аблатив

✓ CHECKS:
  - Count: 4 == 4
  - Contains 'отложительный падеж': True
  - Contains 'отделительный падеж': True
  - Contains 'исходный падеж': True
  - Contains 'аблатив': True
  - No unclosed parens: True
```

### Test 2: Regression tests
```bash
PYTHONPATH=backend python - <<'PY'
from app.database import SessionLocal, init_db
from app.services.article_review import ArticleReviewService

init_db()
with SessionLocal() as session:
    service = ArticleReviewService(session)
    
    payload_270, _ = service.reparse_article('eo', 270)
    payload_383, _ = service.reparse_article('eo', 383)
    
    print(f"Article 270: {len(payload_270['groups'])} groups (expected: 24)")
    print(f"Article 383: {len(payload_383['groups'])} groups (expected: 45)")
PY
```

### Test 3: Code compiles
```bash
PYTHONPATH=backend python -m compileall backend/app/services/translation_review.py
```

## Success Criteria

- [ ] Article 57: 4 items (3 adjective+noun + аблатив)
- [ ] No unclosed parentheses in output
- [ ] No text fragments (like "исходный)" or "(или отделительный")
- [ ] Article 270: 24 groups (no regression)
- [ ] Article 383: 45 groups (no regression)
- [ ] Code compiles without errors

## Implementation Hints

1. **Find the class:** Search for `class _PhraseBuilder` in translation_review.py (around line 1850)
2. **Find the method:** Look for `def add_alternatives(self, options: Sequence[str])`
3. **Replace the method** with the fixed version above
4. **Key insight:** When note alternatives arrive, the word BEFORE the note is already in `self.components[-1][-1]` - extract it and add as first alternative!
5. **Edge case:** Make sure to handle when there's no word before note (just add alternatives as-is)

## Complexity Assessment

⭐⭐ (2/5) - MEDIUM
- Only ONE method to modify
- Logic is straightforward: extract last word from last component, add to alternatives
- ~30 lines of code
- No new functions needed

## Context Files to Read (if needed)

- `/home/avo/rueo_global/backend/app/services/translation_review.py` - main file to edit
- Look at `_extract_note_alternatives()` around line 2007 to see what alternatives it extracts

## Expected Time

15-30 minutes
