# Context for Issue #12 Fix

## Project Overview

Esperanto↔Russian dictionary parser. We're fixing translation group generation bugs.

## What You're Fixing

**Issue #12:** Alternative expansion with `_или_` (Russian "or") is broken.

**Example problem:**
```
Input: "отложительный (_или_ отделительный, _или_ исходный) падеж"
Current output: 2 broken groups with fragments
Expected: 3 combinations of adjective+noun
```

## Key System Components

### _PhraseBuilder class
**Location:** `/home/avo/rueo_global/backend/app/services/translation_review.py` around line 1850

**Purpose:** Builds translation phrases by accumulating words and alternatives.

**Key data structure:**
```python
self.components: List[List[str]]  # Each component is list of alternatives
```

**Example flow:**
1. Parser sees: `"отложительный (_или_ отделительный) падеж"`
2. Adds TEXT: `"отложительный"` → components = `[['отложительный']]`
3. Adds NOTE alternatives: `['отделительный']` via `add_alternatives()`
4. Adds TEXT: `"падеж"` → components = `[...alternatives..., ['падеж']]`
5. Cross product: generates all combinations

### The Bug

Method `add_alternatives()` receives alternatives FROM the note (`['отделительный']`), but the FIRST variant (`'отложительный'`) was already added as regular text BEFORE the note arrived.

**Current behavior:** Alternatives list is incomplete (missing first variant)
**Fix needed:** Extract first variant from last component, include it in alternatives

## Testing Commands

### Reparse article
```bash
PYTHONPATH=backend python - <<'PY'
from app.database import SessionLocal, init_db
from app.services.article_review import ArticleReviewService

init_db()
with SessionLocal() as session:
    payload, _ = ArticleReviewService(session).reparse_article('eo', 57)
    
    for g in payload['groups']:
        print(f"Section: {g.get('section')}")
        print(f"Items: {g['items']}")
PY
```

### Check group count
```bash
PYTHONPATH=backend python - <<'PY'
from app.database import SessionLocal, init_db
from app.services.article_review import ArticleReviewService

init_db()
with SessionLocal() as session:
    payload, _ = ArticleReviewService(session).reparse_article('eo', 270)
    print(f"Groups: {len(payload['groups'])}")
PY
```

## Database Setup

Database is already initialized. Just use:
```python
from app.database import SessionLocal, init_db

init_db()
with SessionLocal() as session:
    # your code
```

## Code Style

- Use type hints
- Add docstrings to modified methods
- Follow existing code patterns
- Keep changes minimal

## Success Criteria

1. Article 57 has 4 items (not broken fragments)
2. All items are complete phrases (no unclosed parentheses)
3. Regression tests pass (articles 270, 383)

## File to Modify

**Only one file:** `/home/avo/rueo_global/backend/app/services/translation_review.py`

**Specific target:** Method `add_alternatives()` in class `_PhraseBuilder`

## Hints

- The fix is LOCAL to one method
- You're not adding new logic, just fixing existing alternatives handling
- Key insight: word before note = first variant
- Use `str.split()` to extract last token from text

## Read First

1. `TASK_ISSUE12_V2_FOCUSED.md` - detailed task with solution
2. Look at `_PhraseBuilder` class structure
3. Look at how `add_alternatives()` is called (search for usage)

Good luck! This is a focused, well-defined fix.
