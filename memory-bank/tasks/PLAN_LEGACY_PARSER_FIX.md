# Plan: Fix Legacy Parser Complex Notes Issue (Issue #2)

## Executive Summary

**Goal:** Fix legacy parser issue with complex notes containing `=` and `<references>`

**Example bug:**
```
Input:  счёты (_прибор_ = <globkalkulilo>, <bidkalkulilo>);
Output: [text: 'счёты'], [text: ', )']  ← BROKEN!
```

**Strategy:** Phased approach with incremental fixes and continuous testing

**Risk Level:** ⭐⭐⭐⭐ (4/5) - High (1912 lines of legacy code)

**Estimated Effort:** 4-6 hours across multiple phases

## Prerequisites - READ FIRST

### Context Files
1. `/home/avo/rueo_global/PARSER_ARCHITECTURE_NOTES.md` - Investigation results
2. `/home/avo/rueo_global/Agents.md` - Project overview
3. Test Article: Article 10, line 3 (the broken case)

### Key Understanding
- Legacy parser is in `/backend/app/parsing/parser_v2.0_clean.py` (1912 lines)
- Used by `LexemeNumberedTemplate` for numbered articles (1., 2., 3., ...)
- Problem: Multiline structure breaks note parsing when:
  - Note contains `= <ref>` pattern
  - Followed by continuation line
  
### Success Criteria
- [ ] Article 10 creates 4 groups (currently 3)
- [ ] Group 3 contains 'счёты' (currently missing)
- [ ] No regressions in articles 270 (24 groups), 383 (45 groups), 54 (3 items)
- [ ] Full reparse succeeds on all 46k+ articles

---

## PHASE 1: Understand the Bug (Research Phase)

**Goal:** Locate exact point where parsing breaks

**Deliverable:** Document with line numbers where bug occurs

### Task 1.1: Trace parse flow for Article 10

```python
# Test: Parse article 10 and inspect structure at each step
from app.parsing.parser_v3.legacy_bridge import legacy_parser

article_text = """[abak/o] 1. _архит._ аб`ак(а);
\t2. _ист._ аб`ак(а), счётная доск`а (_древний счётный прибор_);
\t3. счёты (_прибор_ = <globkalkulilo>, <bidkalkulilo>);
\t\tjapana ~ _см._ <sorobano>;
\t4. _мат._ аб`ак(а), номогр`амма."""

# Step 1: Test parse_rich_text on isolated note
note_text = "_прибор_ = <globkalkulilo>, <bidkalkulilo>"
result = legacy_parser.parse_rich_text(f"({note_text})")
print("Isolated note parsing:", result)

# Step 2: Test full article parsing
result = legacy_parser.parse_article(article_text)
block3 = [b for b in result['body'] if b.get('number') == 3][0]
print("Block 3 content:", block3.get('content'))
print("Block 3 children:", block3.get('children'))
```

**Expected findings:**
- Isolated note parsing works (from PARSER_ARCHITECTURE_NOTES.md)
- Full article parsing breaks
- Difference is in multiline handling

### Task 1.2: Identify key functions

Search `parser_v2.0_clean.py` for:
1. `def parse_article` - Entry point (line ~1740)
2. `def parse_rich_text` - Text parsing (works correctly)
3. `def process_final_tree` - Multiline processing (line ~1576)
4. Note handling functions (grep for "note")

**Key question:** Where does multiline continuation interfere with note?

### Task 1.3: Reproduce minimal test case

Create minimal failing input:
```python
# Minimal test that should work but doesn't
test_minimal = """[test/o] 1. word (_note_ = <ref>);
\t\tcontinuation;"""

result = legacy_parser.parse_article(test_minimal)
# Does this break too? If yes, problem is simpler than Article 10
```

**Deliverable 1:** Document titled "Bug Location Report"
- Exact function(s) where parsing breaks
- Line numbers
- Minimal reproduction case
- Hypothesis of root cause

---

## PHASE 2: Design the Fix (Planning Phase)

**Goal:** Design fix WITHOUT implementing yet

**Prerequisites:** Phase 1 complete

### Task 2.1: Analyze note parsing logic

Study how notes are currently parsed:
1. How does `parse_rich_text` handle `(_note_)`?
2. How does multiline logic interact with notes?
3. Where is the `', )'` garbage created?

### Task 2.2: Design fix approach

**Option A: Fix note boundary detection**
- If problem is note closing paren detection
- Fix regex or parsing logic to handle `= <ref>` inside

**Option B: Fix multiline continuation**
- If problem is continuation line splitting note
- Fix `process_final_tree` to preserve note integrity

**Option C: Two-stage parsing**
- First pass: extract and protect notes
- Second pass: process multiline
- Third pass: restore notes

**Decision criteria:**
- Minimal code changes (lower risk)
- Clear fix logic (easier to test)
- No impact on other features

**Deliverable 2:** "Fix Design Document"
- Chosen approach with justification
- Pseudocode of changes
- List of functions to modify
- Test cases to verify fix

---

## PHASE 3: Implement Fix (Coding Phase)

**Goal:** Implement designed fix incrementally

**Prerequisites:** Phase 2 complete, design approved

### Task 3.1: Create test suite FIRST

Before changing code, create tests:

```python
# File: backend/app/parsing/test_legacy_parser_fix.py

def test_complex_note_parsing():
    """Test note with = and references"""
    text = "счёты (_прибор_ = <globkalkulilo>, <bidkalkulilo>)"
    result = legacy_parser.parse_rich_text(text)
    
    assert len(result) == 2
    assert result[0]['type'] == 'text'
    assert result[0]['text'] == 'счёты '
    assert result[1]['type'] == 'note'
    # Note should be complete, not broken

def test_article_10_parsing():
    """Full Article 10 test"""
    # ... full article text ...
    result = legacy_parser.parse_article(article_text)
    
    blocks = result['body']
    block3 = [b for b in blocks if b.get('number') == 3][0]
    
    # Should have 'счёты' in content
    content_texts = [c.get('text') for c in block3.get('content', [])]
    assert 'счёты' in content_texts
    
    # Should NOT have garbage
    assert ', )' not in str(content_texts)
```

**Run tests:** They should FAIL before fix (proving they catch the bug)

### Task 3.2: Implement fix (based on Phase 2 design)

**Guidelines:**
- Change ONE function at a time
- Run tests after EACH change
- Commit after each working change
- Keep changes minimal

**Example implementation structure:**
```python
# If fix is in process_final_tree (line ~1576)

def process_final_tree(tree, in_note_context=False, note_base_indent=None):
    # BEFORE (broken):
    # ... existing logic that breaks notes ...
    
    # AFTER (fixed):
    # Add check: if processing note, preserve it as single unit
    # ... new logic ...
    
    # Keep rest unchanged
```

### Task 3.3: Test incrementally

After each change:
```bash
# Run specific tests
PYTHONPATH=backend python backend/app/parsing/test_legacy_parser_fix.py

# Verify no syntax errors
PYTHONPATH=backend python -m compileall backend/app/parsing/parser_v2.0_clean.py
```

**Deliverable 3:** Working fix with passing tests

---

## PHASE 4: Integration Testing (Validation Phase)

**Goal:** Verify fix works in full system

**Prerequisites:** Phase 3 complete, tests passing

### Task 4.1: Test Article 10 end-to-end

```python
from app.database import SessionLocal, init_db
from app.services.article_review import ArticleReviewService

init_db()
with SessionLocal() as session:
    payload, _ = ArticleReviewService(session).reparse_article('eo', 10)
    
    print(f"Groups: {len(payload['groups'])}")
    # Should be 4, not 3
    
    # Check for 'счёты' group
    has_schyoty = any('счёт' in str(g['items']) for g in payload['groups'])
    print(f"Has счёты group: {has_schyoty}")  # Should be True
```

**Success:** 4 groups with 'счёты' present

### Task 4.2: Regression testing

```bash
# Test reference articles
PYTHONPATH=backend python - <<'PY'
from app.database import SessionLocal, init_db
from app.services.article_review import ArticleReviewService

init_db()
with SessionLocal() as session:
    service = ArticleReviewService(session)
    
    p270, _ = service.reparse_article('eo', 270)
    p383, _ = service.reparse_article('eo', 383)
    p54, _ = service.reparse_article('eo', 54)
    
    print(f"Article 270: {len(p270['groups'])} (expected: 24)")
    print(f"Article 383: {len(p383['groups'])} (expected: 45)")
    
    # Check Issue #5/#9 still works
    for g in p54['groups']:
        if '~iĝ/i' in g.get('section', ''):
            print(f"Article 54 [~iĝ/i]: {len(g['items'])} (expected: 3)")
PY
```

**Success:** All numbers match expectations

### Task 4.3: Sample reparse (careful!)

Test on small sample:
```bash
# Reparse first 100 articles
PYTHONPATH=backend python - <<'PY'
from app.database import SessionLocal, init_db
from app.services.article_parser import ArticleParserService

init_db()
with SessionLocal() as session:
    parser = ArticleParserService(session)
    
    errors = []
    for art_id in range(1, 101):
        try:
            result = parser.parse_article_by_id('eo', art_id)
            if not result.success:
                errors.append(art_id)
        except Exception as e:
            errors.append((art_id, str(e)))
    
    print(f"Parsed: 100, Errors: {len(errors)}")
    if errors:
        print(f"Failed articles: {errors[:10]}")
PY
```

**Success:** 0 errors (or same errors as before fix)

**Deliverable 4:** Test report confirming fix works

---

## PHASE 5: Full Deployment (Optional - High Risk)

**Goal:** Apply fix to all articles

**WARNING:** Only proceed if Phases 1-4 are 100% successful

### Task 5.1: Backup current state

```bash
# Backup database
pg_dump rueo_db > backup_before_parser_fix.sql

# Backup parsing states
PYTHONPATH=backend python - <<'PY'
from app.database import SessionLocal
from app.models import ArticleParseState
import json

with SessionLocal() as session:
    states = session.query(ArticleParseState).filter_by(lang='eo').all()
    backup = [{'art_id': s.art_id, 'parsed_payload': s.parsed_payload} for s in states]
    
    with open('backup_parse_states.json', 'w') as f:
        json.dump(backup, f)
    
    print(f"Backed up {len(states)} parse states")
PY
```

### Task 5.2: Full reparse with monitoring

```bash
PYTHONPATH=backend python - <<'PY'
from app.database import SessionLocal, init_db
from app.services.article_parser import ArticleParserService
import time

init_db()
start = time.time()
errors = []

with SessionLocal() as session:
    parser = ArticleParserService(session)
    
    for art_id in range(1, 46378):
        try:
            result = parser.parse_article_by_id('eo', art_id)
            if not result.success:
                errors.append(art_id)
            
            if art_id % 1000 == 0:
                elapsed = time.time() - start
                print(f"Progress: {art_id}/46377 ({art_id/463.77:.1f}%), errors: {len(errors)}, time: {elapsed:.1f}s")
        
        except Exception as e:
            errors.append((art_id, str(e)))
            if len(errors) > 10:
                print(f"Too many errors ({len(errors)}), stopping!")
                break

print(f"\nFinal: Errors: {len(errors)}")
if errors:
    print(f"First 10: {errors[:10]}")
PY
```

**Success criteria:** Errors ≤ errors from baseline (before fix)

---

## Rollback Plan (If Something Goes Wrong)

### If tests fail in Phase 3:
```bash
# Discard changes
git checkout backend/app/parsing/parser_v2.0_clean.py

# Return to Phase 2, redesign fix
```

### If regression tests fail in Phase 4:
```bash
# Rollback code
git checkout backend/app/parsing/parser_v2.0_clean.py

# Restore database if needed
psql rueo_db < backup_before_parser_fix.sql
```

### If full reparse fails in Phase 5:
```bash
# Restore parse states
PYTHONPATH=backend python - <<'PY'
from app.database import SessionLocal
from app.models import ArticleParseState
import json

with open('backup_parse_states.json') as f:
    backup = json.load(f)

with SessionLocal() as session:
    for item in backup:
        state = session.query(ArticleParseState).filter_by(
            lang='eo', art_id=item['art_id']
        ).first()
        if state:
            state.parsed_payload = item['parsed_payload']
    
    session.commit()
    print("Restored parse states")
PY
```

---

## Decision Points

### After Phase 1:
- **If bug location unclear:** STOP, investigate more
- **If multiple bugs found:** Prioritize, fix one at a time
- **If fix looks too complex:** POSTPONE, document findings

### After Phase 2:
- **If no safe fix design:** STOP, consider alternative approach
- **If design requires >200 line changes:** Reconsider, too risky

### After Phase 3:
- **If tests don't pass:** Debug, don't proceed to Phase 4
- **If fix creates new issues:** Rollback, redesign

### After Phase 4:
- **If regressions found:** STOP, analyze impact
- **If sample reparse has errors:** Don't proceed to Phase 5

---

## Communication Protocol

### Progress Reports

After each phase, create summary:
```
PHASE X COMPLETE:
- Status: SUCCESS / PARTIAL / FAILED
- Key findings: ...
- Changes made: ...
- Tests results: ...
- Next steps: ...
```

### Asking for Help

If stuck:
1. Document what you tried
2. Show error messages
3. Ask specific question
4. Provide minimal reproduction

---

## Estimated Timeline

- **Phase 1:** 1-2 hours (research)
- **Phase 2:** 30-60 min (design)
- **Phase 3:** 1-2 hours (implementation)
- **Phase 4:** 30-60 min (testing)
- **Phase 5:** 1-2 hours (deployment) - OPTIONAL

**Total:** 4-6 hours (Phases 1-4 only)

---

## Success Metrics

### Must Have (Phase 1-4)
- [ ] Article 10: 4 groups (not 3)
- [ ] Group with 'счёты' exists
- [ ] No regressions in test articles
- [ ] Tests pass

### Nice to Have (Phase 5)
- [ ] Full reparse successful
- [ ] Zero new errors
- [ ] Performance unchanged

---

## Additional Notes

### Why Phased Approach?

1. **Risk Management:** Can stop at any phase if issues found
2. **Incremental Progress:** Each phase delivers value
3. **Learning:** Understand code before changing it
4. **Testing:** Verify at each step

### Alternative if Legacy Fix Too Hard

If fix proves too difficult:
- Document findings in detail
- Create separate task for template rewrite
- Accept limitation for now
- Focus on other issues

---

## Getting Started

1. Read PARSER_ARCHITECTURE_NOTES.md
2. Start with Phase 1, Task 1.1
3. Report findings after each task
4. Don't proceed to next phase without approval

**Good luck!** This is a challenging but structured task.
