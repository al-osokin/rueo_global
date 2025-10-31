# Parser Architecture Notes (Issue #2 Investigation)

## Problem
Article 10, line 3: `счёты (_прибор_ = <globkalkulilo>, <bidkalkulilo>);`

Parser returns:
```
[0] text: 'счёты'
[1] divider: ','
[2] text: ')'  ← BROKEN! Should be note, not text
```

## Investigation Trail

### Step 1: text_parser.py (NEW parser)
**Location:** `backend/app/parsing/parser_v3/text_parser.py`

**Test result:**
```python
parse_rich_text("счёты (_прибор_ = <globkalkulilo>, <bidkalkulilo>)")
# Returns:
[0] text: 'счёты '
[1] note: '_прибор_ = <globkalkulilo>, <bidkalkulilo>'  ← CORRECT!
```

**Conclusion:** text_parser.py works correctly ✓

### Step 2: Template Selection
**Location:** `backend/app/parsing/parser_v3/templates.py`

Article 10 uses `LexemeNumberedTemplate` (line 223):
- Detects numbered entries (1., 2., 3., 4.)
- **DELEGATES to legacy_parser.parse_article()** (line 254)
- Does NOT use text_parser.py!

**Problem identified:** Legacy parser is still used for numbered articles!

### Step 3: Legacy Parser
**Location:** `backend/app/parsing/parser_v2.0_clean.py` (1912 lines)

This is the OLD regex-based parser that has known issues with complex notes.

**Architecture decision:**
- parser_v3 was meant to replace legacy parser
- But some templates still delegate to legacy parser
- `LexemeNumberedTemplate` is one of them

## Root Cause

**The bug is in legacy_parser.py note handling**, not in text_parser.py.

Options:
1. Fix legacy_parser (complex, 1912 lines)
2. Rewrite LexemeNumberedTemplate to use text_parser (better long-term)
3. Post-process fix in normalization.py (band-aid)

## Template Architecture Overview

```
pipeline.py
  └─> select_template()
       ├─> LetterEntryTemplate (A, a) - uses text_parser ✓
       ├─> MorphemeNumberedTemplate ([-a I]) - uses legacy_parser
       ├─> MorphemeArticleTemplate ([-a]) - uses legacy_parser  
       ├─> LexemeNumberedTemplate ([abak/o] 1. 2. 3.) - uses legacy_parser ← Issue #2
       └─> DefaultArticleTemplate - uses legacy_parser
```

**Status:** Most templates still use legacy parser!

## Next Steps

Need to check how legacy parser processes notes with `=` and `<...>` inside.

## Detailed Investigation Results

### Test: Legacy parser with full article

**Input (line 3):**
```
3. счёты (_прибор_ = <globkalkulilo>, <bidkalkulilo>);
	japana ~ _см._ <sorobano>;
```

**Legacy parser output:**
```
Block 3:
  Content: [
    {type: 'text', text: 'счёты'},
    {type: 'text', text: ', )'}  ← BROKEN!
  ]
  Children: [
    {type: 'explanation', content: [{text: '(прибор'}]},  ← Incomplete!
    {type: 'translation', ...}  (japana ~)
  ]
```

**Problem identified:**
1. Note `(_прибор_ = <globkalkulilo>, <bidkalkulilo>)` is split incorrectly
2. Only `'(прибор'` ends up in explanation child
3. The rest becomes garbage text `, )` in content
4. Issue appears to be in **multiline structure handling** (continuation line breaks note)

### Root Cause Hypothesis

Legacy parser has issues when:
- Note contains `=` and `<...>` references
- Note is followed by continuation line (japana ~)
- Multiline parsing interferes with note extraction

This is NOT a simple fix - requires deep changes to legacy parser multiline logic.

## Possible Solutions

### Option A: Fix in legacy_parser.py
- **Pros:** Fixes root cause
- **Cons:** Complex (1912 lines), risky, affects all numbered articles
- **Effort:** High (3-5 hours)

### Option B: Post-process fix in normalization.py
- **Pros:** Safer, isolated change
- **Cons:** Band-aid, doesn't fix root cause
- **Effort:** Medium (1-2 hours)
- **Approach:** Detect broken `, )` pattern and reconstruct note

### Option C: Rewrite LexemeNumberedTemplate to use text_parser
- **Pros:** Long-term correct solution, removes legacy dependency
- **Cons:** Requires implementing numbered value logic from scratch
- **Effort:** Very High (5-8 hours)

### Option D: Skip for now
- **Pros:** Focus on easier issues
- **Cons:** Article 10 remains broken
- **Effort:** 0

## Recommendation

**Option B** - Post-process fix in normalization.py:
1. Detect pattern: content ends with `, )`
2. Check if children[0] is explanation with `'('` prefix
3. Reconstruct full note from source text
4. Fix content and children

This is the safest quick fix that doesn't touch legacy parser.

## Attempted Fix (Rolled Back)

**Date:** 2025-10-31

**Approach:** Post-process fix in normalization.py

**Implementation:**
- Created `_fix_broken_complex_note()` function
- Detected pattern: content ends with `, )`
- Removed garbage from content
- Moved valid text into children as separate translation

**Result:** PARTIAL SUCCESS
- ✓ Garbage `, )` successfully removed
- ✓ New translation child created with 'счёты'
- ❌ Translation_review still didn't create separate group
- ❌ Final output: 3 groups instead of expected 4

**Root issue:** Problem deeper than expected
- Block structure was fixed at parser level
- BUT translation_review logic doesn't process it correctly
- Possibly filtered as duplicate or merged with other groups
- Requires deeper investigation into _collect_groups_from_blocks()

**Decision:** ROLLED BACK
- Fix incomplete, doesn't solve the full problem
- Would require changes in both normalization.py AND translation_review.py
- Time investment > benefit for single edge case
- Issue #2 postponed for future deep dive

**Lessons learned:**
1. Legacy parser issues cascade through multiple layers
2. Fixing at normalization level is insufficient
3. Need full understanding of translation_review logic
4. Some issues require coordinated changes across multiple files

## Status: POSTPONED

Issue #2 requires more comprehensive solution:
- Either fix legacy parser (high risk, high effort)
- OR rewrite LexemeNumberedTemplate completely (very high effort)
- OR accept limitation and document edge case

**Token investment:** ~30k tokens
**Time investment:** ~1.5 hours
**Complexity rating:** ⭐⭐⭐⭐⭐ (5/5) - Very High
