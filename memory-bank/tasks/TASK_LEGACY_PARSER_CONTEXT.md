# Context: Legacy Parser Fix Task

## Quick Start

You're tasked with fixing a bug in the legacy parser (parser_v2.0_clean.py).

**Main document:** `/home/avo/rueo_global/PLAN_LEGACY_PARSER_FIX.md`

**Start here:** Phase 1, Task 1.1

## The Bug in 30 Seconds

**Article 10, line 3:**
```
счёты (_прибор_ = <globkalkulilo>, <bidkalkulilo>);
```

**Current output:** BROKEN
- Content: `[text: 'счёты'], [text: ', )']` ← garbage!
- Result: Missing translation group

**Expected output:** WORKING
- Content: `[text: 'счёты'], [note: '...']`
- Result: 4 groups (currently 3)

## Why This Matters

- Affects ALL numbered articles (1., 2., 3., ...)
- ~10k+ articles use `LexemeNumberedTemplate`
- Legacy parser handles these articles
- Bug loses translation data

## Project Context

### File Structure
```
backend/app/parsing/
├── parser_v2.0_clean.py        ← FIX HERE (1912 lines, legacy)
├── parser_v3/
│   ├── text_parser.py          ← New parser (works correctly)
│   ├── templates.py            ← Template selection
│   ├── legacy_bridge.py        ← Bridge to old parser
│   └── normalization.py        ← Post-processing
```

### Why Legacy Parser Still Used?

- parser_v3 was supposed to replace it
- BUT most templates still delegate to legacy parser
- `LexemeNumberedTemplate` is one of them
- Rewriting templates = huge effort
- Fixing legacy parser = smaller effort

### Investigation Already Done

See `PARSER_ARCHITECTURE_NOTES.md` for:
- Root cause analysis
- What was tried
- Why it was postponed
- Architecture insights

## Your Mission

**Phase 1:** Understand WHERE the bug occurs (1-2 hours)
- Trace parsing flow
- Identify exact line numbers
- Create minimal reproduction

**Phase 2:** Design the fix (30-60 min)
- Analyze options
- Choose safest approach
- Write pseudocode

**Phase 3:** Implement fix (1-2 hours)
- Write tests FIRST
- Change code incrementally
- Test after each change

**Phase 4:** Validate (30-60 min)
- Test Article 10
- Regression test
- Sample reparse

**Phase 5 (OPTIONAL):** Full deployment
- Only if Phases 1-4 perfect
- Requires backup
- High risk

## Success Criteria (Phases 1-4)

- [ ] Article 10 creates 4 groups (not 3)
- [ ] Contains 'счёты' translation
- [ ] No ', )' garbage in output
- [ ] Article 270: 24 groups (no regression)
- [ ] Article 383: 45 groups (no regression)
- [ ] Article 54: 3 items in [~iĝ/i] (Issue #5/#9 still works)

## Testing Commands

### Test Article 10
```python
from app.database import SessionLocal, init_db
from app.services.article_review import ArticleReviewService

init_db()
with SessionLocal() as session:
    payload, _ = ArticleReviewService(session).reparse_article('eo', 10)
    print(f"Groups: {len(payload['groups'])} (expected: 4)")
    
    # Check for 'счёты'
    for g in payload['groups']:
        if 'счёт' in str(g['items']):
            print(f"Found: {g['items']}")
```

### Test Legacy Parser Directly
```python
from app.parsing.parser_v3.legacy_bridge import legacy_parser

article_text = """[abak/o] 1. _архит._ аб`ак(а);
\t2. _ист._ аб`ак(а), счётная доск`а (_древний счётный прибор_);
\t3. счёты (_прибор_ = <globkalkulilo>, <bidkalkulilo>);
\t\tjapana ~ _см._ <sorobano>;
\t4. _мат._ аб`ак(а), номогр`амма."""

result = legacy_parser.parse_article(article_text)
block3 = [b for b in result['body'] if b.get('number') == 3][0]

print("Content:", block3.get('content'))
# Should have 'счёты', NOT ', )'
```

### Regression Test
```python
from app.database import SessionLocal, init_db
from app.services.article_review import ArticleReviewService

init_db()
with SessionLocal() as session:
    service = ArticleReviewService(session)
    
    p270, _ = service.reparse_article('eo', 270)
    p383, _ = service.reparse_article('eo', 383)
    p54, _ = service.reparse_article('eo', 54)
    
    print(f"270: {len(p270['groups'])} (expect: 24)")
    print(f"383: {len(p383['groups'])} (expect: 45)")
    
    # Issue #5/#9 check
    for g in p54['groups']:
        if '~iĝ/i' in g.get('section', ''):
            print(f"54 [~iĝ/i]: {len(g['items'])} (expect: 3)")
```

## Important Files to Read

1. **PLAN_LEGACY_PARSER_FIX.md** - Complete plan (read this!)
2. **PARSER_ARCHITECTURE_NOTES.md** - Investigation findings
3. **Agents.md** - Project overview
4. **backend/app/parsing/parser_v2.0_clean.py** - The file to fix

## Communication

After EACH phase, report:
- Status: SUCCESS / PARTIAL / FAILED
- Key findings
- Next steps
- Any blockers

## Decision Tree

```
Phase 1 → Can you find the bug location?
  Yes → Proceed to Phase 2
  No → STOP, report findings, ask for help

Phase 2 → Can you design a safe fix?
  Yes → Proceed to Phase 3
  No → STOP, discuss alternatives

Phase 3 → Do tests pass?
  Yes → Proceed to Phase 4
  No → Debug, or rollback and redesign

Phase 4 → Any regressions?
  No → SUCCESS! Consider Phase 5
  Yes → STOP, analyze impact

Phase 5 → Full reparse OK?
  Yes → COMPLETE SUCCESS!
  No → Rollback, document findings
```

## Risk Management

**Low Risk (Phases 1-2):** Research only, no code changes

**Medium Risk (Phase 3):** Code changes, but tested

**High Risk (Phase 4):** Integration testing

**Very High Risk (Phase 5):** Full deployment

**Always:** Can rollback with `git checkout parser_v2.0_clean.py`

## Expected Complexity

- **Phase 1:** ⭐⭐ (2/5) - Research
- **Phase 2:** ⭐⭐⭐ (3/5) - Design
- **Phase 3:** ⭐⭐⭐⭐ (4/5) - Implementation
- **Phase 4:** ⭐⭐⭐ (3/5) - Testing
- **Phase 5:** ⭐⭐⭐⭐⭐ (5/5) - Deployment (OPTIONAL)

## Tips

1. **Don't rush:** Understand before changing
2. **Test continuously:** After every change
3. **Keep changes minimal:** Less code = less risk
4. **Document findings:** Help future debugging
5. **Ask questions:** Better than breaking things

## Starting Point

```python
# Your first command:
# Understand current behavior on Article 10

from app.parsing.parser_v3.legacy_bridge import legacy_parser

test_text = "счёты (_прибор_ = <globkalkulilo>, <bidkalkulilo>)"
result = legacy_parser.parse_rich_text(test_text)

print("Isolated parsing:", result)
# This should work (returns note correctly)

# Now test in full article context...
```

---

**Ready?** Start with Phase 1, Task 1.1 in PLAN_LEGACY_PARSER_FIX.md

**Questions?** Ask BEFORE making changes

**Good luck!** 🚀
