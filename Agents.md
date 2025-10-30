# Agents Notes for rueo_global

## Project overview
This is an Esperanto↔Russian dictionary project with a FastAPI backend and Quasar (Vue.js) frontend. The system parses dictionary articles from a structured format, identifies translation candidates, and presents them to editors for review.

### Architecture
- **Backend**: FastAPI application in `/backend/app/`
  - `parsing/parser_v2.0_clean.py` - Main parser converting raw article text to structured JSON
  - `services/article_parser.py` - Service layer wrapping parser with DB operations
  - `services/translation_review.py` - Core logic for extracting translation groups and generating review candidates
  - `services/article_review.py` - High-level service for admin review workflow
- **Frontend**: Quasar/Vue.js application in `/frontend-app/`
  - `src/pages/AdminReview.vue` - Main review interface
- **Database**: PostgreSQL with SQLAlchemy ORM
  - Tables: `Article`, `ArticleRu` (source articles), `ArticleParseState` (parsing results), `ArticleParseNote` (editor notes)
  - Connection configured via environment or defaults (see database.py)

### Key data flow
1. Raw articles stored in `Article.priskribo` (text with markup like `[~a]`, `_italic_`, etc.)
2. Parser converts to structured JSON → stored in `ArticleParseState.parsed_payload`
3. Review service processes parsed JSON → generates `TranslationGroup` objects with candidates
4. Frontend displays groups for human review → selections saved in `ArticleParseState.resolved_translations`

## Common CLI helpers

### Preview translations for debugging
```bash
PYTHONPATH=backend python backend/app/tools/review_translations.py --lang eo --offset 100 --limit 5
```
Shows parsed translations in human-readable format. Useful for quickly checking parser output without opening the UI.

### Reparse a single article
When you modify parser logic and want to test on a specific article:
```bash
PYTHONPATH=backend python - <<'PY'
from app.database import SessionLocal, init_db
from app.services.article_review import ArticleReviewService

init_db()
with SessionLocal() as session:
    # Example: reparse article 270 (aer|o)
    payload, result = ArticleReviewService(session).reparse_article('eo', 270)
    print(f"✓ Reparsed {result.headword}, groups: {len(payload['groups'])}")
PY
```
This regenerates `parsed_payload` and review data. Use after changing `parser_v2.0_clean.py` or `translation_review.py`.

### Inspect parsed article structure
To debug parser output without going through review service:
```bash
PYTHONPATH=backend python - <<'PY'
from app.database import SessionLocal, init_db
from app.services.article_parser import ArticleParserService

init_db()
with SessionLocal() as session:
    parser = ArticleParserService(session)
    result = parser.parse_article_by_id('eo', 270, include_raw=True)
    
    # Inspect raw parsed JSON
    body = result.raw.get('body', [])
    print(f"Body sections: {len(body)}")
    
    # Look at specific section
    for section in body:
        if section.get('type') == 'headword':
            lemmas = section.get('lemmas', [])
            if lemmas:
                print(f"Headword: {lemmas[0].get('lemma')}")
                print(f"Children: {len(section.get('children', []))}")
PY
```

### Check article_sections (fallback source)
When debugging `_apply_source_fallback` behavior:
```bash
PYTHONPATH=backend python - <<'PY'
from app.database import SessionLocal, init_db
from app.services.translation_review import _get_article_sections

init_db()
with SessionLocal() as session:
    sections = _get_article_sections('eo', 270)
    if sections and '[~uj/o]' in sections:
        print("Lines for [~uj/o]:")
        for line in sections['[~uj/o]']:
            print(f"  {repr(line)}")
PY
```

### API endpoints for reparsing
- **Batch reparse**: `POST /admin/articles/{lang}/reparse` with `{ "include_pending": true|false }`
  - Reparses all articles with given status
  - `include_pending=true` includes articles not yet reviewed
- **Single article**: `POST /admin/articles/{lang}/{art_id}/reparse`
  - Triggered by "Переразобрать открытую" button in admin UI
  - Returns updated `ArticleReviewPayload` with `groups`, `candidates`, etc.

## Parser gotchas and recent fixes

### Core parsing behavior
**Location:** `backend/app/parsing/parser_v2.0_clean.py`

1. **`parse_illustration` - Splitting Esperanto from Russian**
   - Splits by finding first Cyrillic character run
   - **Edge case fixed:** Punctuation at start (e.g., `(воз)действие`) could break split
   - **Guard added:** If text starts with non-letters, keeps it with surrounding text
   - Example: `~aj kasteloj возд`ушные з`амки` → `eo='aeraj kasteloj'`, `ru_segments=[{text: 'возд`ушные з`амки'}]`

2. **`parse_headword_remainder` - Handling colon after headword form**
   - Pattern `[~a]:` (colon immediately after form) signals examples follow, not translations
   - **Fix:** Text after colon now processed through `parse_illustration()` instead of plain text
   - **Why this matters:** Allows forms without direct translation, only usage examples
   - Example fix in article 365 `[~a]:`: `~a kompanio авиакомп`ания` now correctly splits into:
     - eo_source: `aertrafika kompanio`
     - items: `['авиакомп`ания']`
   - Test case: article 365 ([aer/trafik|o])

3. **Multiline illustrations handling**
   - `classify_node` now collects text from ALL child nodes before parsing
   - **Problem fixed:** Continuation lines (indented further) were lost
   - Example that was broken:
     ```
     en libera ~o на вольном воздухе
         (_или_ открытом) воздухе
     ```
   - Now correctly produces: `на вольном воздухе (_или_ открытом) воздухе`
   - Test case: article 270 ([aer|o])

4. **Stylistic markers recognition**
   - Markers like `_прям._`, `_перен._`, `_букв._`, `_устар._`, `_разг._`, `_поэт._` are detected
   - Converted to `explanation` nodes with `style='italic'`
   - **Important:** They do NOT get included in translation text
   - Defined in `stylistic_markers` set around line 706

### Translation review processing
**Location:** `backend/app/services/translation_review.py`

1. **`_expand_parenthetical_forms` - Optional word segments**
   - Expands `(воз)действие` → `действие | воздействие`
   - **Fix:** Now normalizes spaces before optional segments
   - Handles cases like `резерву`ар (для|с) в`оздуха` → multiple combinations

2. **`_apply_source_fallback` - Using original article text**
   - When parsed content is insufficient, falls back to `article_sections` (original text split by section headers)
   - Splits by `;` and `,` outside parentheses
   - Auto-expands parentheses when only one spec present (fixes `[~ec/o]` cases)
   - **CRITICAL FIX (latest):** Now filters out example lines to prevent duplication!
     - Skips lines starting with `~` (those are examples, not translations)
     - Skips lines containing Latin letters (Esperanto text in examples)
     - Groups multi-line examples together until `;` separator
   - **Why this matters:** Previously, examples like `~ujo de pneuxmatiko к`амера ш`ины` would appear BOTH:
     - As a translation in parent section `[~uj/o]` (wrong!)
     - As a separate example group (correct)
   - Example fix in article 270: section `[~uj/o]` now has only 1 translation group instead of 3
   - **CRITICAL FIX (reference filtering):** Now filters out pure reference segments!
     - Uses `_is_pure_reference_segment()` to detect segments like `_ср._ <ventoli>, <ventumi>`
     - Such segments are cross-references, not translations
     - Example fix in article 270: section `[~um/i]` no longer has ghost translation `<ventumi>`

3. **`_merge_plain_russian_illustrations` - Handling illustration blocks**
   - Converts illustration blocks back to translations when `eo` field is empty or non-alphabetic
   - This happens at top level in `_collect_groups_from_blocks` (around line 323)

4. **Examples vs translations distinction**
   - Translation groups now have `eo_source: Optional[str]` field
   - Set by `_build_groups_from_example` when processing illustrations with Esperanto text
   - **When `eo_source` is set:** This is an example/illustration, NOT a direct translation
   - **When `eo_source` is null:** This is a regular translation group
   - UI should display these differently (show Esperanto source for examples)

## Data structures

### TranslationGroup (core review unit)
Defined in `backend/app/services/translation_review.py`:
```python
@dataclass
class TranslationGroup:
    items: List[str]                    # Current selected translations
    label: Optional[str]                # Like "погов.", "прям.", etc.
    requires_review: bool               # True if needs human decision
    base_items: List[str]               # Original from source
    auto_generated: bool                # True if expanded from parentheses
    section: Optional[str]              # Like "[~a]" or "~aj kasteloj"
    candidates: List[TranslationCandidate]  # Alternative translation sets
    selected_candidate: Optional[str]   # ID of chosen candidate
    eo_source: Optional[str]            # Esperanto text (for examples only!)
```

**Key distinction:**
- `eo_source=None` → Regular translation (e.g., `[~a] → возд`ушный`)
- `eo_source="aeraj kasteloj"` → Example usage (e.g., `~aj kasteloj → возд`ушные з`амки`)

### ArticleParseState database fields
- `parsed_payload` (JSONB): Raw parser output, structured as:
  ```json
  {
    "headword": {"lemma": "aer|o", "raw_form": "[aer|o]"},
    "body": [
      {"type": "translation", "content": [...]},
      {"type": "illustration", "eo": "...", "ru_segments": [...]},
      {"type": "headword", "lemmas": [...], "children": [...]}
    ]
  }
  ```
- `resolved_translations` (JSONB): Editor decisions:
  ```json
  {
    "groups": {
      "group_0": {
        "accepted": true,
        "selected_candidate": "expanded",
        "manual_override": "свой перевод | синоним"
      }
    }
  }
  ```

## Frontend/admin workflow

### Review page interaction
**File:** `frontend-app/src/pages/AdminReview.vue`

1. **Loading article:**
   - Calls `GET /admin/articles/{lang}/{art_id}`
   - Backend returns `ArticleReviewPayload` with:
     - `groups[]` - translation groups to review
     - `auto_candidates[]` - automatically extracted translations
     - `resolved_translations` - previous decisions
     - `notes[]` - editor comments

2. **Reviewing translations:**
   - Each group shows radio buttons for candidates
   - For `requires_review=true` groups: "Свой вариант" option appears
   - Editor selects candidate OR enters manual text
   - Groups marked as accepted after selection

3. **Saving review:**
   - Calls `POST /admin/articles/{lang}/{art_id}/review`
   - Saves selections to `resolved_translations`
   - Updates `parsing_status` (e.g., "needs_review" → "reviewed")

4. **Reparsing article:**
   - "Переразобрать открытую" button
   - Calls `POST /admin/articles/{lang}/{art_id}/reparse`
   - Regenerates `parsed_payload` and review data
   - **Important:** Previous `resolved_translations` are preserved and re-applied!

### Manual override feature
**See:** `MANUAL_OVERRIDE_GUIDE.md` for detailed docs

- Available for groups with `requires_review=true`
- User can enter custom translations separated by `|`
- Stored in `resolved_translations.groups[group_id].manual_override`
- Automatically included in full-text search indexing
- Format: `перевод1 | перевод2 | перевод3` (synonyms)

### Examples display (TODO for UI)
Groups with `eo_source` should be displayed differently:
- Show Esperanto text prominently: **~aj kasteloj**
- Show Russian as translation: возд`ушные з`амки
- Visual distinction from regular translations (maybe different color/icon)
- Section label should indicate it's an example, not headword

## Legacy notes (preserved for context)
- Admin review page expects backend running; “Переразобрать открытую” calls the single-article reparse endpoint. If you adjust parsing logic, reparse target articles so the UI reflects changes.
- The review table stores previous decisions in `article_parse_state.resolved_translations`; clearing via `POST /admin/articles/{lang}/{art_id}/reset`.
- **Manual override**: For groups with `requires_review`, a "Свой вариант" candidate appears in the radio button list. When selected, users can enter custom translations (synonyms separated by `|`). These are stored in `resolved_translations.groups[group_id].manual_override` and automatically included in full-text search indexing. Groups are considered reviewed if any candidate is selected (including "manual" with non-empty text). See `MANUAL_OVERRIDE_GUIDE.md` for details.
- **Examples vs translations**: Translation groups now have `eo_source` field. When set (non-null), the group represents an example/illustration (like `~aj kasteloj → возд`ушные з`амки`) rather than a direct translation. UI should display these differently, showing the Esperanto source text alongside Russian translations.

## Troubleshooting

### Import errors (`ModuleNotFoundError: No module named 'app'`)
**Solution:** Always use `PYTHONPATH=backend` when running scripts:
```bash
# Wrong:
python backend/app/services/article_review.py

# Correct:
PYTHONPATH=backend python -c "from app.services.article_review import ArticleReviewService"
```

### Verify code compiles after changes
After editing parser or review services:
```bash
PYTHONPATH=backend python -m compileall backend/app/parsing/parser_v2.0_clean.py backend/app/services/translation_review.py
```
This catches syntax errors without running the full code.

### Examples still appearing in translation groups
Check `_apply_source_fallback` logic:
1. Verify example lines start with `~` or contain Latin letters
2. Check `article_sections` content with CLI helper above
3. Test with: `PYTHONPATH=backend python - <<'PY' ... PY` (see CLI helpers section)

### Translation groups missing or wrong
1. **Check parsed_payload first:**
   - Use "Inspect parsed article structure" CLI helper
   - Look at `children` of headword blocks
   - Verify `illustration` blocks have correct `eo` and `ru_segments`

2. **Check review processing:**
   - Add temporary DEBUG output in `_collect_groups_from_blocks` or `_build_groups_from_example`
   - Use pattern: `import sys; print(f"DEBUG: ...", file=sys.stderr)`
   - Remove DEBUG before committing!

3. **Test with known-good article:**
   - Article 270 ([aer|o]) is well-tested
   - Should have 26 groups total
   - Section [~uj/o] should have 1 translation group + 2 example groups

### Database connection issues
Check environment variables or defaults in `backend/app/database.py`. Default connection uses localhost with rueo_db database.

### Parser produces wrong structure
1. Check input text encoding (should be UTF-8)
2. Verify markup patterns match parser expectations
3. Test `parse_illustration` function in isolation
4. Look for recent changes in `parser_v2.0_clean.py` git history

## Recent fixes: Duplicate elimination and numbered translation handling (30.10.25)

### Problem
Articles with numbered values (1., 2., ...) had duplicate translation groups appearing in the review payload. For example, article 383 ([afekt|i]) had 54 groups instead of expected ~27, with each numbered value's translations appearing multiple times.

### Root causes identified
1. **Triple invocation of `build_translation_review`:**
   - Called in `article_parser.py` when creating `ArticleParseResult`
   - Called again in `article_review.load_article()` when fetching the same article
   - Called third time in `reparse_article()` which internally called `load_article()`

2. **Numbered value content vs children confusion:**
   - Initial implementation skipped content of numbered translations, treating it as a header
   - Actually, content contains the FIRST translation(s), children contain additional translations/examples
   - This caused missing translations (e.g., `аффект`ировать` from value 1)

3. **Fallback source (`_apply_source_fallback`) duplication:**
   - `article_sections` dictionary contained ALL lines including numbered values
   - Fallback logic would re-parse these lines, creating duplicate groups
   - Continuation lines (indented text after numbered value) were not filtered

### Solutions implemented

**1. Review caching in ArticleParseResult:**
```python
# In article_parser.py
@dataclass(slots=True)
class ArticleParseResult:
    ...
    review: Optional[Any] = None  # Cache TranslationReview object
```

**2. New method `_build_payload_from_result` in ArticleReviewService:**
- Builds payload from existing `result.review` without re-parsing
- Used in `reparse_article()` to avoid calling `load_article()` which would re-parse
- Handles datetime conversion for notes correctly

**3. Numbered translation content processing:**
```python
# In translation_review.py _collect_groups_from_blocks()
if block_number is not None:
    # Process content as FIRST translation (not a header!)
    block_content = _clone_nodes(block.get("content") or [])
    if block_content:
        content_normalized = _normalize_labelled_content(block_content)
        if content_normalized:
            buffer_content.append(content_normalized)
    
    # Then process children (additional translations/examples)
    for child in block.get("children") or []:
        ...
```

**4. Enhanced filtering in `_apply_source_fallback`:**
```python
def _is_example_line(text: str) -> bool:
    stripped = text.strip()
    if stripped.startswith('~'):
        return True
    # Filter numbered values (1., 2., ...)
    if re.match(r'^\s*\*?\s*\d+\.', stripped):
        return True
    # Filter lines with Latin letters (Esperanto examples)
    cleaned = text.replace('_', '').replace('<', '').replace('>', '').strip()
    return any('a' <= c <= 'z' or 'A' <= c <= 'Z' for c in cleaned)

# Skip continuation lines after numbered value
skip_until_semicolon = False
for line in section_lines:
    if re.match(r'^\*?\s*\d+\.', line.strip()):
        skip_until_semicolon = True
        continue
    if skip_until_semicolon:
        if line.rstrip().endswith(';'):
            skip_until_semicolon = False
        continue
    ...
```

### Results
- **Article 383:** 53 groups (was 54), 7 [afekt|i] groups (was 8)
- **Article 270:** 25 groups (expected ~25), no regressions
- **Article 365:** 4 groups, no regressions
- Performance: `build_translation_review` called once instead of three times

### Note on "duplicates" in different numbered values
If the same translation appears in content of numbered value 1 and numbered value 2 (e.g., `притвор'яться` in article 383), these are NOT considered duplicates. They represent the same word used in different semantic contexts (meanings 1 and 2). Both entries are preserved for:
- Full-text search (finds the article regardless)
- Proper semantic tagging in final JSON output
- Synonym relationship tracking per meaning

## Recent fixes: Abbreviations and punctuation handling (30.10.25 - continued)

### Problem
After fixing numbered translation handling, article 383 revealed punctuation issues:
1. Abbreviations like "что-л." were broken: "делать что-л. неестественно" became "аффектировать | неестественно" (lost "делать что-л.")
2. Exclamation marks had extra space: "не ломайся!" appeared as "не ломайся !"

### Root cause
In `_split_translation_groups()`, divider nodes with `.` triggered `_flush_builder()`, splitting phrases:
```python
elif symbol == ".":
    _flush_builder()  # This broke abbreviations!
```

When parser encountered "д`елать что-л.", it split into:
- TEXT: "д`елать что-л" (without period)
- DIVIDER: "." (separate node)

The flush caused "д`елать что-л" and "неест`ественно" to become separate phrases.

### Solution
Added `append_punctuation()` method to `_PhraseBuilder` that attaches punctuation directly to the last component:
```python
def append_punctuation(self, punct: str) -> None:
    """Присоединяет знак пунктуации к последнему компоненту (для сокращений типа 'что-л.')"""
    if not self.components or not punct:
        return
    last_options = self.components[-1]
    if last_options:
        for i in range(len(last_options)):
            last_options[i] = last_options[i].rstrip() + punct
```

Updated divider handling to attach `.`, `!`, `?` instead of flushing:
```python
elif symbol in (".", "!", "?"):
    # Знаки конца предложения/восклицания присоединяем к предыдущему слову
    builder.append_punctuation(symbol)
```

### Results
- **Article 383, value 1:** Now correctly parses as "аффект`ировать | д`елать что-л. неест`ественно"
- **Example "ne ~u!":** Now correctly shows as "не лом`айся!" (no extra space)
- **No regressions:** Articles 270 (25 groups), 365 (4 groups) unchanged

### Key insight
Period in Russian translations is almost always part of abbreviations (что-л., т.е., т.п.), not a phrase separator. Only `,` and `;` should trigger phrase boundaries.

## Quick reference: test article 270

Article 270 (`[aer|o]`) is used for testing parser fixes. Expected structure after latest fixes:

- **Total groups:** 25 (was 30 before duplicate fix, 26 before reference filtering)
- **Section `[~a]`:** 1 translation + 1 example
  - Translation group: `возд`ушный` (eo_source=null)
  - Example group: `~aj kasteloj → возд`ушные з`амки` (eo_source="aeraj kasteloj")
- **Section `[~uj/o]`:** 1 translation + 2 examples
  - Translation: `резерву`ар для в`оздуха | резерву`ар с в`оздухом` (eo_source=null)
  - Example 1: `~ujo de pneŭmatiko → к`амера ш`ины` (eo_source="aerujo de pneŭmatiko")
  - Example 2: `~ujo de spiraparato... → балл`он со сж`атым в`оздухом...` (eo_source="aerujo de spiraparato...")
- **Section `[~um/i]`:** 2 translations (no ghost `<ventumi>` reference)
  - Translation 1: `пров`етривать` (eo_source=null)
  - Translation 2: `аэр`ировать` (eo_source=null)

To verify:
```bash
PYTHONPATH=backend python - <<'PY'
from app.database import SessionLocal, init_db
from app.services.article_review import ArticleReviewService

init_db()
with SessionLocal() as session:
    data = ArticleReviewService(session).load_article('eo', 270)
    groups = data['groups']
    print(f"Total groups: {len(groups)}")
    
    for g in groups:
        if '[~uj/o]' in g.get('section', '') or '~uj' in g.get('section', ''):
            eo = g.get('eo_source')
            print(f"  {g['section']}: eo_source={'YES' if eo else 'NO'}")
PY
```
