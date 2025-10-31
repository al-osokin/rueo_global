# Task: Issue #12 - Expansion of `_или_` Alternatives

## CRITICAL FINDING - Root Cause Identified!

**The problem is NOT in how notes are processed!**

Parser correctly identifies `(_или_ ...)` as a NOTE node.  
Function `_extract_note_alternatives()` (line 2007) correctly extracts alternatives from notes.  
BUT it only sees content INSIDE parentheses, not words BEFORE or AFTER!

Example from article 57:
```
Text: "отлож`ительный (_или_ отдел`ительный, _или_ исх`одный) пад`еж"

Parser produces:
1. TEXT: "отлож`ительный "
2. NOTE: "_или_ отдел`ительный, _или_ исх`одный"  ← Only alternatives!
3. TEXT: " пад`еж"

_extract_note_alternatives() returns: ['отдел`ительный', 'исх`одный']
Missing: 'отлож`ительный' (the first variant before parentheses!)
```

**Real problem:** The note alternatives are added via `builder.add_alternatives()` but the FIRST variant (before parentheses) is added as regular text separately!

## Problem Statement

Articles contain alternatives marked with `_или_` (or) in parentheses, but they are not being expanded into ALL combinations with surrounding words.

### Current Behavior (Article 57)

**Source text:**
```
[ablativ/o] * _грам._ отлож`ительный (_или_ отдел`ительный, _или_ исх`одный) пад`еж, аблат`ив.
```

**Current output (WRONG):**
- Group 1: `['отлож\`ительный (или отдел\`ительный']` ← незакрытая скобка!
- Group 2: `['исх\`одный) пад\`еж', 'аблат\`ив']` ← начинается с середины!

**Expected output:**
- `['отлож\`ительный пад\`еж', 'отдел\`ительный пад\`еж', 'исх\`одный пад\`еж', 'аблат\`ив']`
- 3 combinations (adjective + noun) + 1 synonym (аблатив)

## Pattern Examples

### Pattern 1: Parentheses AFTER word
```
ель обыкнов`енная (_или_ европ`ейская)
→ ['ель обыкнов\`енная', 'ель европ\`ейская']
```

### Pattern 2: Parentheses BEFORE word
```
отлож`ительный (_или_ отдел`ительный, _или_ исх`одный) пад`еж
→ ['отлож\`ительный пад\`еж', 'отдел\`ительный пад\`еж', 'исх\`одный пад\`еж']
```

### Pattern 3: Parentheses IN MIDDLE of phrase
```
пит`ать (_или_ исп`ытывать) отвращ`ение
→ ['пит\`ать отвращ\`ение', 'исп\`ытывать отвращ\`ение']
```

### Pattern 4: Between two words
```
цен`а (_или_ ст`оимость) подп`иски
→ ['цен\`а подп\`иски', 'ст\`оимость подп\`иски']
```

## Requirements

Create function `_expand_ili_alternatives()` that:

1. **Detects pattern:** text with `(_или_ ...)` or `(..., _или_ ...)` parentheses
2. **Extracts alternatives:** splits by `, _или_` or `_или_` inside parentheses
3. **Identifies anchor word:** word(s) that combine with alternatives
4. **Generates combinations:** creates all variants
5. **Works with ANY part of speech:** nouns, verbs, adjectives, etc.
6. **Handles both positions:** parentheses before OR after anchor word

## Implementation Location

**File:** `/home/avo/rueo_global/backend/app/services/translation_review.py`

**Where to add:**
- After `_expand_adjective_list()` function (around line 1685)
- Call it in both processing paths (lines ~300 and ~683)

## Solution Approach

The fix needs to be in `_PhraseBuilder.add_alternatives()` method!

When alternatives from note are added, we need to ALSO include the word that was added just BEFORE the note as the FIRST alternative.

**Location:** Line ~1890 in `_PhraseBuilder` class

**Current code (approximate):**
```python
def add_alternatives(self, options: Sequence[str]) -> None:
    """Adds alternatives that should combine with following words"""
    if not options:
        return
    self.components.append(list(options))  # Just adds alternatives from note
```

**Fixed code:**
```python
def add_alternatives(self, options: Sequence[str]) -> None:
    """
    Adds alternatives that should combine with following words.
    If we have pending text in current component, add it as FIRST alternative.
    """
    if not options:
        return
    
    # Check if we have a word in the last component (before the note)
    # If yes, it's the FIRST variant that alternatives replace
    alternatives = list(options)
    
    if self.components and self.components[-1]:
        # Last component has words - extract the last word as first variant
        last_words = self.components[-1][0] if isinstance(self.components[-1], list) else self.components[-1]
        tokens = last_words.split()
        if tokens:
            # Last token before note is the first variant
            first_variant = tokens[-1].strip()
            
            # Remove that word from the last component
            remaining = ' '.join(tokens[:-1]).strip()
            if remaining:
                self.components[-1] = [remaining]
            else:
                # No words left, remove the component
                self.components.pop()
            
            # Add first variant at the beginning of alternatives
            alternatives = [first_variant] + alternatives
    
    self.components.append(alternatives)
```

## Implementation Steps

1. Find `_PhraseBuilder` class (around line 1850-1900)
2. Find `add_alternatives()` method
3. Replace with the fixed version above
4. Test with article 57

## OLD ALGORITHM BELOW - IGNORE!

This was the original plan before finding the real root cause.  
The fix is actually MUCH simpler - just modify `add_alternatives()` method!

<details>
<summary>Click to expand old algorithm (not needed)</summary>

```python
def _expand_ili_alternatives_OLD(items: List[str]) -> List[str]:
    """
    Раскрывает альтернативы с _или_ в скобках.
    
    Примеры:
    - "слово (_или_ синоним)" → ["слово", "синоним"]
    - "(_или_ вариант1, _или_ вариант2) слово" → ["вариант1 слово", "вариант2 слово"]
    - "начало (_или_ середина) конец" → ["начало конец", "середина конец"]
    """
    result = []
    
    for item in items:
        # Check if item contains _или_ in parentheses
        if '(_или_' not in item and '_или_' not in item:
            result.append(item)
            continue
        
        # Pattern: (...(_или_ alt1, _или_ alt2)...)
        expanded = _expand_ili_pattern(item)
        if expanded and len(expanded) > 1:
            result.extend(expanded)
        else:
            result.append(item)
    
    return _deduplicate(result)
```

### Step 2: Extract and expand alternatives
```python
def _expand_ili_pattern(text: str) -> List[str]:
    """
    Раскрывает одну строку с _или_ альтернативами.
    
    Returns:
        List of expanded variants, or empty list if pattern not found
    """
    import re
    
    # Find parenthetical group with _или_
    # Pattern: (word1 _или_ word2, _или_ word3)
    pattern = r'\(([^)]*_или_[^)]*)\)'
    match = re.search(pattern, text)
    
    if not match:
        return []
    
    # Extract text before, inside, and after parentheses
    paren_start = match.start()
    paren_end = match.end()
    before = text[:paren_start].strip()
    inside = match.group(1)
    after = text[paren_end:].strip()
    
    # Split alternatives by _или_ (with or without comma)
    # Remove italic markers from _или_
    alternatives_text = inside.replace('_или_', '|SPLIT|')
    parts = [p.strip() for p in alternatives_text.split('|SPLIT|') if p.strip()]
    
    # Clean up: remove leading/trailing commas
    alternatives = []
    for part in parts:
        cleaned = part.strip().strip(',').strip()
        if cleaned:
            alternatives.append(cleaned)
    
    if not alternatives:
        return []
    
    # Generate combinations
    results = []
    
    # If first alternative is empty/very short, it's a prefix pattern
    # Example: "(_или_ отделительный, _или_ исходный) падеж"
    # First part before _или_ is the base word before parentheses
    if before:
        # Check if alternatives should go BEFORE or AFTER anchor word
        if after:
            # Middle position: "начало (_или_ вариант) конец"
            for alt in alternatives:
                combined = f"{before} {alt} {after}".strip()
                results.append(_clean_spacing(combined))
        else:
            # After position: "слово (_или_ синоним)"
            # Add both: original word AND alternatives
            results.append(_clean_spacing(before))
            for alt in alternatives:
                results.append(_clean_spacing(alt))
    elif after:
        # Before position: "(_или_ вариант1, _или_ вариант2) слово"
        for alt in alternatives:
            combined = f"{alt} {after}".strip()
            results.append(_clean_spacing(combined))
    
    return results if results else []
```

### Step 3: Integrate into processing pipeline

**Location 1: `_collect_groups_from_blocks` (around line 300)**
```python
items = _normalize_compound_terms(items)
# Раскрываем списки прилагательных: "adj1, adj2 noun" -> "adj1 noun | adj2 noun"
items = _expand_adjective_list(items)
# Раскрываем альтернативы с _или_: "word (_или_ alt)" -> "word | alt"
items = _expand_ili_alternatives(items)
```

**Location 2: `_build_groups_from_example` (around line 683)**
```python
expanded_items = _normalize_compound_terms(expanded_items)
# Раскрываем списки прилагательных
expanded_items = _expand_adjective_list(expanded_items)
# Раскрываем альтернативы с _или_
expanded_items = _expand_ili_alternatives(expanded_items)
```

## Test Cases

### Test 1: Article 57 (main test case)
```python
PYTHONPATH=backend python - <<'PY'
from app.database import SessionLocal, init_db
from app.services.article_review import ArticleReviewService

init_db()
with SessionLocal() as session:
    payload, _ = ArticleReviewService(session).reparse_article('eo', 57)
    
    print("=== Article 57 after fix ===")
    for g in payload['groups']:
        items = g['items']
        print(f"Section: {g.get('section')}")
        print(f"Items: {items}")
        print(f"Expected: 4 items (3 adjective+noun combinations + аблатив)")
        print(f"Actual count: {len(items)}")
        print()
PY
```

**Expected:**
- One group with 4 items: `['отлож\`ительный пад\`еж', 'отдел\`ительный пад\`еж', 'исх\`одный пад\`еж', 'аблат\`ив']`

### Test 2: Article 50 (after pattern)
```python
# "ель обыкновенная (_или_ европейская)"
# Expected: ['ель обыкнов\`енная', 'ель европ\`ейская']
```

### Test 3: Article 65 (middle pattern)
```python
# "питать (_или_ испытывать) отвращение"
# Expected: ['пит\`ать отвращ\`ение', 'исп\`ытывать отвращ\`ение']
```

### Test 4: Regression - no _или_ pattern
```python
# Article 270 should still have 25 groups (no regression)
# Article 383 should still have 48 groups
```

## Edge Cases

1. **Multiple _или_ in one group:** `(_или_ alt1, _или_ alt2, _или_ alt3)`
2. **Nested parentheses:** Should NOT expand if parentheses are nested
3. **No anchor word:** `(_или_ вариант)` without before/after text - just extract alternatives
4. **Empty alternatives:** Skip empty parts after splitting

## Important Notes

1. **Clean italic markers:** `_или_` is an italic marker, remove underscores from splits
2. **Preserve stress marks:** Keep grave accents `` ` `` in all variants
3. **Clean spacing:** Use `_clean_spacing()` helper for all results
4. **Deduplicate:** Use `_deduplicate()` to remove duplicate variants
5. **Non-greedy matching:** Use `[^)]*` to avoid matching multiple parenthetical groups

## Success Criteria

- [ ] Article 57 shows 4 items: 3 adjective combinations + аблатив
- [ ] No unclosed parentheses in output
- [ ] Article 50 shows 2 variants (before/after pattern works)
- [ ] Article 270: 25 groups (no regression)
- [ ] Article 383: 48 groups (no regression)
- [ ] All `_или_` markers removed from output
- [ ] Code compiles: `python -m compileall backend/app/services/translation_review.py`

## Files to Modify

- `/home/avo/rueo_global/backend/app/services/translation_review.py` (only file)

## Hints

- Study existing `_expand_adjective_list()` function for similar pattern
- Use `_clean_spacing()` helper (already exists)
- Use `_deduplicate()` helper (already exists)
- Look at `_expand_parenthetical_forms()` for parentheses handling patterns
- Regex pattern to find parentheses with _или_: `r'\(([^)]*_или_[^)]*)\)'`
- Split alternatives: replace `_или_` with separator, then split

## Expected Complexity

⭐ (1/5) - EASY!
- Just modify ONE method `add_alternatives()` in `_PhraseBuilder` class
- About 15-20 lines of code
- Logic is clear from the example above

</details>
