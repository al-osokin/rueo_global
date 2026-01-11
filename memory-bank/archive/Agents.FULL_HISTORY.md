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

## Major refactoring: New text_parser.py replacing legacy regex-based parsing (30.10.25)

### Problem
The entire parser v3 was actually a **wrapper around legacy v2.0_clean.py**, which used regex-based splitting:
```python
parts = re.split(r'(_|<[^>]+>|\([^)]+\)|\{[^}]+\}|[,;:.!?])', text)
```
This approach split on **ALL** periods, including abbreviations, causing systematic issues.

### Architecture before refactoring
- **parser_v3/**: Template selection layer (LetterEntry, StandardDictionary, etc.)
- **parser_v2.0_clean.py**: Actual parsing via `legacy_parser.parse_rich_text()`, `parse_headword()`, etc.
- Result: Band-aids in translation_review.py to fix parser output post-factum

### Solution: Complete rewrite of core parsing functions
Created `/backend/app/parsing/parser_v3/text_parser.py` with:

**1. Smart `parse_rich_text()` - Character-by-character parsing instead of regex split:**
```python
def is_abbreviation_context(text: str, position: int) -> bool:
    """Check if period at position is part of abbreviation"""
    # Patterns: что-л., т.е., т.п., и т.д., см., ср.
    # Uses regex patterns + context checking
```

**2. Clean `parse_headword()` - Proper bracket and lemma parsing:**
- Handles `[aer|o]`, `[~a]`, `[A, a]`
- Extracts official marks (`*`), homonym numbers
- No regex splitting, direct character processing

**3. Accurate `split_ru_segments()` - Converts parsed nodes to segments:**
- Handles reference labels (см., ср.)
- Categorizes dividers correctly (near/far/sentence)
- Preserves context for multi-step processing

**4. Simple `preprocess_text()` - Text normalization:**
- Line ending normalization
- Trailing space cleanup
- No complex transformations

### Integration
Replaced all `legacy_parser.*` calls in:
- `parser_v3/templates.py` - All template classes
- `parser_v3/normalization.py` - Segment processing
- `parser_v3/pipeline.py` - Article preprocessing

### Results
- ✅ **Article 383**: "аффект`ировать | д`елать что-л. неест`ественно" (abbreviation preserved)
- ✅ **Examples**: "не лом`айся!" (no extra space before exclamation)
- ✅ **No regressions**: Articles 270 (25 groups), 365 (4 groups) unchanged
- ✅ **Performance**: Same speed, cleaner code

### Key differences from legacy approach
| Aspect | Legacy (v2.0_clean) | New (text_parser) |
|--------|---------------------|-------------------|
| Splitting | `re.split()` on all punctuation | Character-by-character with context |
| Abbreviations | No special handling | Smart detection via patterns |
| Maintainability | 1900 lines, complex logic | ~500 lines, clear functions |
| Dependencies | Circular imports, global state | Clean imports, stateless |

### Next steps (optional)
- Remove translation_review.py band-aids (append_punctuation method now unnecessary)
- Deprecate parser_v2.0_clean.py entirely
- Add unit tests for text_parser.py
- Document abbreviation patterns for future additions

### Legacy code status
`parser_v2.0_clean.py` is still present but **no longer used** in parser_v3 flow. It remains for:
- Historical reference
- Potential standalone usage
- Gradual deprecation

Can be safely removed after full validation.

## Full reparse after refactoring (30.10.25)

### Preparation
After major parser refactoring, all parsing states were reset:
- Deleted all comments (23) for lang='eo'
- Deleted all parsing states (46,356) for lang='eo'
- Cleared database for fresh start

### Recursion protection fix
Fixed infinite recursion bug in `_expand_parenthetical_forms()`:
- **Problem**: Article 39 caused infinite recursion on nested parentheses
- **Solution**: 
  * Added MAX_DEPTH = 50 limit
  * Added `seen_texts` set to detect loops
  * Pass `depth` parameter through all recursive calls

### Full reparse results
```
Total articles:  46,377
Success:         46,377 (100%)
Errors:          0
Time:            82.1 seconds
Speed:           ~565 articles/second
```

### Validation
All test articles passed:
- **Article 270** [aer|o]: 25 groups ✓
- **Article 365** [aer/trafik|o]: 4 groups ✓
- **Article 383** [afekt|i]: 53 groups ✓
  - Abbreviation 'что-л.' preserved ✓
  - Exclamation mark 'не ломайся!' without space ✓

### Status
- ✅ **All 46k+ articles parsed successfully**
- ✅ **Zero errors** with new text_parser.py
- ✅ **Ready for editor review** from scratch
- ✅ **Clean foundation** for continuing work

## Editor review findings - First 60 articles (30.10.25)

После полного reparse проведена проверка первых 60 статей. Найдены **системные проблемы**, требующие исправления в парсере и review logic.

### Категория: Обработка опциональных частей и скобок

**1. Склейка слов с граве при раскрытии опциональных частей**
- **Статья 2**: `[a-vort/o] (_только в эсперанто_) (\`имя) прилаг\`ательное`
- Ожидалось: `прилагательное | \`имя прилагательное` (с пробелом!)
- Получено: `прилагательное | \`имяприлагательное` (слипание)
- **Статус**: Частично исправлено в parser_v2.0_clean.py (добавлена проверка `starts_with_grave`), но проблема сохраняется
- **Причина**: Пробел теряется где-то в pipeline после парсера (возможно normalization.py или _expand_parenthetical_forms)

**6. Неправильная обработка опциональных частей после слова**
- **Статья 39**: `аберрация, отклонение (от нормы)`
- Ожидалось: `отклонение | отклонение от нормы`
- Получено: парсер захватывает `"(от"` с открывающей скобкой
- **Причина**: Скобки после слова обрабатываются неправильно

### Категория: Примечания и метаданные

**2. Примечания со ссылками и знаком равенства**
- **Статья 10**: `счёты (_прибор_ = <globkalkulilo>, <bidkalkulilo>);`
- Проблема: примечание не обрабатывается, остаётся `)` и склеивается со следующей строкой
- Получено: `')japana ~ sorobano'` как второй вариант перевода
- **Причина**: Сложные примечания с `=` и `<...>` не распознаются правильно

**11. Курсивный текст попадает в переводы**
- **Статья 56**: `иссечение | удаление`
- Получено: `"иссечение | удалениеили органа ср"`
- Проблема: курсив `_или органа_` и `_ср._` включаются в перевод
- **Причина**: Курсивные пояснения и начала отсылок не фильтруются

**13. Метки официальности `*1`, `*2`, ... `*10` не распознаются**
- **Статья 58**: Звёздочка с номером дополнения (`*2`)
- Проблема: звёздочка удаляется, но цифра попадает в текст перевода
- Должно: сохраняться в `official_mark` в metadata
- **Причина**: Парсер не обрабатывает паттерн `*N` для дополнений Академии

### Категория: Отсылки и ссылки

**4. Примеры с отсылками не фильтруются**
- **Статьи 19, 23**: `~a tifo`, `(natura) ~ujo`
- Проблема: строки с тильдой (~) - это примеры, должны быть отдельными группами или отфильтрованы
- Сейчас: склеиваются с переводами

**8. Отсылки `_ср._ <...>` не фильтруются**
- **Статьи 52, 56**: `_ср._ <Etiopio>`
- Проблема: создаётся группа с содержимым `"<"` вместо фильтрации
- Должно: reference блоки с `_ср._`, `_см._` игнорируются

**10. Статьи только с отсылками создают пустые группы**
- **Статья 55**: Оба пункта - только отсылки
- Проблема: создаётся группа с содержимым `"1"` (номер значения)
- Должно: если статья содержит только reference - групп не создаётся вообще

### Категория: Раскрытие сокращений и альтернатив

**3. Не раскрываются прилагательные перед существительным**
- **Статья 19**: `"брюшной, задний плавник"`
- Ожидалось: `"брюшной плавник | задний плавник"`
- Получено: только исходный вариант без раскрытия
- **Статья 42**: `"аббевильская, шелльская, древнеашельская эпоха"` + `"... культура"`
- Ожидалось: по 3 комбинации для каждого существительного (всего 6 вариантов)
- **Причина**: Функция `_split_leading_adjectives` не срабатывает

**12. Не раскрываются альтернативы с `_или_` в примечаниях**
- **Статья 57**: `отложительный (_или_ отделительный, _или_ исходный) падеж, аблатив`
- Ожидалось: 4 варианта (3 комбинации прилагательное+существительное + аблатив)
- Проблема: многострочное примечание с `_или_` не раскрывается
- **Причина**: Функция `_extract_note_alternatives` не работает или не применяется

### Категория: Многострочные переводы

**5. Склеивание перевода с примером**
- **Статья 23, форма `[~uj/o]`**: `"улей"` + пример `"(natura) ~ujo"`
- Получено: `"\`улей ~uj..."` (склеено)
- **Причина**: Continuation lines с примерами не распознаются

**9. Многострочные переводы разбиваются неправильно**
- **Статья 54, форма `[~iĝ/i]`**: 3 перевода на разных строках
- Правильно (через `|`):
  - `"окончить среднее учебное заведение"`
  - `"пройти выпускной экзамен"`
  - `"пройти экзамен на аттестат зрелости"`
- Получено: 3 отдельные группы с неправильным разбиением:
  1. `"окончить среднее учебное заведение | пройти выпускной"` (оборвано!)
  2. `"экзамен | пройти экзамен"` (потерян контекст)
  3. `"зрелости"` (только последнее слово)
- **КРИТИЧНО**: Continuation lines должны корректно склеиваться в одну группу

### Категория: UI и кандидаты

**7. Кандидат "Как в источнике" показывает неправильный текст (глобально)**
- Должен: показывать базовый разбор без раскрытия (просто split по `,` и `;`)
- Сейчас: показывает то же самое, что основной вариант
- Пример: `"аберрировать, давать аберрацию"` → кандидат должен быть `"аберрировать | давать аберрацию"`
- **Причина**: Логика генерации base_items кандидата сломана

### Приоритеты исправления

**Критичные (блокируют работу редактора):**
1. Многострочные переводы (#9) - данные теряются
2. Раскрытие прилагательных (#3, #12) - основная функция парсера
3. Фильтрация отсылок (#4, #8, #10) - создаётся мусор

**Важные (снижают качество):**
4. Опциональные части (#1, #6) - частые ошибки
5. Примечания (#2, #11) - неправильная обработка
6. Кандидат "Как в источнике" (#7) - UI сломан

**Низкий приоритет:**
7. Метки официальности (#13) - metadata, не критично
8. Склеивание с примерами (#5) - edge cases

### Следующие шаги
1. ✅ Исправить фронтенд (претензия от редактора) - DONE (31.10.25)
2. Системно исправить критичные проблемы парсера
3. Full reparse после исправлений
4. Повторная проверка первых 60 статей

## PLAN: Fixing parser issues systematically (31.10.25)

### Strategy
**Primary goal:** Fix issues in parser_v3 templates/normalization, NOT in translation_review post-processing.
- Parser_v3 should produce correct semantic structure from the start
- Translation_review should only handle grouping/candidate generation, not fixing parser mistakes
- Eliminate remaining dependencies on legacy parser_v2.0_clean.py

### Current architecture issues
1. **parser_v3/templates.py** - Some templates still call `legacy_parser.parse_article()` (lines 193, 219, 255, 269)
2. **parser_v3/normalization.py** - Uses `legacy_parser` for label registration and KNOWN_SHORTENINGS
3. **translation_review.py** - Has many workarounds fixing parser output (should be minimal after fixing parser)

### Issue resolution plan (grouped by fix location)

#### GROUP A: Fix in parser_v3 text parsing (text_parser.py)
These are fundamental text parsing issues that should be caught during initial parse:

**#2: Complex notes with equals sign and references** (статья 10)
- Problem: `счёты (_прибор_ = <globkalkulilo>, <bidkalkulilo>);` не обрабатывается
- Location: `text_parser.py` - enhance note parsing to handle `=` and references
- Test: статья 10 should properly separate note from translation

**#11: Italic text in translations** (статья 56)
- Problem: `_или органа_` и `_ср._` включаются в перевод
- Location: `text_parser.py` - mark italic segments as explanations/references
- Test: статья 56 should have clean translations without italic markers

**#13: Official marks with numbers** (статья 58)
- Problem: `*2` парсится с потерей звёздочки, цифра попадает в текст
- Location: `text_parser.py` - recognize `*[0-9]+` pattern as official_mark
- Test: статья 58 should have official_mark='*2' in metadata

#### GROUP B: Fix in parser_v3 normalization (normalization.py)
These are issues with segment classification and expansion:

**#1: Grave accent word merging** (статья 2) **[CRITICAL]**
- Problem: `(\`имя) прилаг\`ательное` → `\`имяприлаг\`ательное` (без пробела)
- Location: `normalization.py` `_expand_parenthetical_forms` or earlier
- Check: Does parser_v3 preserve spaces correctly before optional parts?
- Test: статья 2 should give `прилагательное | \`имя прилагательное` (с пробелом)

**#3: Leading adjective expansion** (статьи 19, 42) **[CRITICAL]**
- Problem: `"брюшной, задний плавник"` не раскрывается
- Location: `normalization.py` - `_split_leading_adjectives` not triggered
- Check: Is this called from parser_v3 or only from translation_review?
- Test: статья 19 should give `брюшной плавник | задний плавник`

**#12: Note alternatives with _или_** (статья 57) **[CRITICAL]**
- Problem: `отложительный (_или_ отделительный, _или_ исходный)` не раскрывается
- Location: `normalization.py` - enhance `_extract_note_alternatives`
- Test: статья 57 should give 3 adjective+noun combinations + аблатив

#### GROUP C: Fix in parser_v3 templates (templates.py)
These are structural parsing issues related to article structure:

**#4: Tilde examples in translations** (статьи 19, 23)
- Problem: Строки с `~` (примеры) склеиваются с переводами
- Location: `templates.py` - classify tilde lines as examples, not translations
- Test: статья 23 `[~uj/o]` should separate translation from `(natura) ~ujo` example

**#6: Optional parts after words** (статья 39)
- Problem: `отклонение (от нормы)` → захват `"(от"` с открывающей скобкой
- Location: `templates.py` or `text_parser.py` - fix parenthesis splitting logic
- Test: статья 39 should give `отклонение | отклонение от нормы`

**#10: Articles with only references** (статья 55)
- Problem: Создаётся группа с содержимым `"1"` (номер значения)
- Location: `templates.py` - detect reference-only articles, skip empty groups
- Test: статья 55 should create zero translation groups

#### GROUP D: Fix in translation_review.py (keep minimal)
These SHOULD be in parser, but may require translation_review fixes:

**#5: Multiline translation splitting** (статья 54) **[CRITICAL]**
- Problem: Continuation lines разбиваются неправильно, теряется контекст
- Location: Check parser_v3 first - does it merge continuation lines?
- Fallback: `translation_review.py` `_apply_source_fallback` continuation logic
- Test: статья 54 `[~iĝ/i]` should have 3 complete translations, not fragments

**#8: Reference filtering** (статьи 52, 56)
- Problem: `_ср._ <...>` создаёт группы с `"<"`
- Location: Already has `_is_pure_reference_segment` - extend patterns?
- Test: статья 52/56 should skip reference lines

**#9: Continuation line merging** (статья 54)
- Same as #5 - check if parser_v3 handles this

#### GROUP E: UI/Candidate generation (translation_review.py)
Not parser issues, but review logic:

**#7: "Как в источнике" candidate broken** (глобально)
- Problem: Shows same as main variant instead of simple split by `,` and `;`
- Location: `translation_review.py` - base_items generation logic
- Test: Any article - "Как в источнике" should show unstemmed source

### Implementation order (31.10.25)

**PHASE 1: Critical text parsing (GROUP A)**
1. Issue #13 (official marks) - simple pattern recognition
2. Issue #11 (italic filtering) - enhance stylistic marker detection
3. Issue #2 (complex notes) - extend note parsing

**PHASE 2: Critical normalization (GROUP B)**
1. Issue #1 (grave merging) - **HIGHEST PRIORITY** - affects many articles
2. Issue #3 (leading adjectives) - common pattern
3. Issue #12 (note alternatives) - multiline handling

**PHASE 3: Structural fixes (GROUP C)**
1. Issue #4 (tilde examples) - classification logic
2. Issue #10 (reference-only) - empty group prevention
3. Issue #6 (optional parts) - parenthesis handling

**PHASE 4: Translation review fixes (GROUP D)**
1. Issue #5/#9 (multiline merging) - continuation lines
2. Issue #8 (reference filtering) - extend patterns
3. Issue #7 (candidate base_items) - UI improvement

**PHASE 5: Testing & full reparse**
1. Test all 13 problematic articles (2, 10, 19, 23, 39, 42, 52, 54, 55, 56, 57, 58)
2. Test reference articles (270, 365, 383)
3. Full reparse of all 46k+ articles
4. Review first 100 articles for new issues

### Test articles reference
- **Статья 2** (a-vort/o): grave merging
- **Статья 10** (abak/o): complex notes
- **Статья 19** (abd/omen/o): leading adjectives
- **Статья 23** (abel/o): tilde examples
- **Статья 39** (aber/aci/o): optional parts
- **Статья 42** (abevil/a): multiple leading adjectives
- **Статья 52, 56**: reference filtering
- **Статья 54** (abituri/ent/o): multiline continuation
- **Статья 55** (abisin/o): reference-only
- **Статья 57** (ablativ/o): note alternatives
- **Статья 58** (abnegaci/o): official marks
- **Статья 270** (aer/o): regression testing (25 groups)
- **Статья 365** (aer/trafik/o): regression testing (4 groups)
- **Статья 383** (afekt/i): regression testing (53 groups)

## PHASE 1 Progress: Text parser fixes (31.10.25)

### Issue #13: Official marks with numbers - FIXED ✓
**Problem:** `[abnegacio] *2 самоотв\`ерженность` → цифра `2` попадала в текст перевода
**Solution:** Added filtering in `translation_review.py` `_apply_source_fallback()`:
```python
# Удаляем метки официальности (*N) из начала строки
line = re.sub(r'^\s*\*\d*\s*', ' ', line)
```
Also enhanced `text_parser.py` `parse_headword()` to recognize `*N` pattern after bracket.
**Test:** Article 58 now correctly shows `официальная_метка='OA2'` without `2` in translation text.

### Issue #11: Italic text in translations - PARTIALLY ANALYZED
**Problem:** `иссеч\`ение, удал\`ение (_ткани, члена или органа_)` → получается `удал\`ениеили органа ср`
**Analysis:** Problem occurs in `_split_translation_groups()` BEFORE fallback is called. Italic notes are being concatenated with translation text during parsing/normalization phase.
**Root cause:** Complex multiline notes with `=` signs and references not properly filtered by legacy parser.
**Status:** Requires deeper investigation of parser → normalization → review flow. Postponed to focus on other critical issues.

### Issue #2: Complex notes with equals sign - ANALYZED, COMPLEX
**Problem:** `счёты (_прибор_ = <globkalkulilo>, <bidkalkulilo>);` → остаётся `')japana ~ sorobano'`
**Root cause:** Legacy parser doesn't handle complex notes with `=` and `<references>` inside. Returns `', )'` as text instead of proper note node.
**Location:** `parser_v2.0_clean.py` parse_rich_text() - needs enhanced note parsing logic
**Status:** Requires significant changes to legacy parser. Postponed as it affects DefaultArticleTemplate flow.

### Issue #1: Grave accent word merging - ANALYZED, ELUSIVE BUG
**Problem:** `(\`имя) прилаг\`ательное` → `\`имяприлаг\`ательное` (пробел исчезает)
**Deep investigation:** 
- `_expand_parenthetical_forms()` works correctly: returns `'\`имя прилаг\`ательное'` WITH space
- `_clean_spacing()`, `_normalize_compound_terms()` preserve space
- Problem occurs somewhere in pipeline AFTER expansion but BEFORE final group items
- Parser correctly returns `'(\`имя) прилаг\`ательное'` (before expansion)
**Status:** Complex bug, requires systematic tracing through entire _split_translation_groups() → _expand_cross_product() → final items flow. Likely in some edge case handling or character-level processing. **POSTPONED** due to complexity and token budget.

### Issue #3: Leading adjectives expansion - ANALYZED, NEEDS NEW LOGIC
**Problem:** `брюшн`ой, з`адний плавн`ик` → should be `брюшн`ой плавн`ик | з`адний плавн`ик`
**Current behavior:** `_split_leading_adjectives()` only works for label='т.е.' (то есть)
**Root cause:** Need to detect pattern "adj1, adj2 noun" and expand BEFORE expansion pipeline
**Location:** Should be in normalization.py or early in translation_review.py
**Status:** Requires new pattern matching logic. _expand_cross_product() doesn't handle this case (different suffixes).

### Issue #8: Reference filtering - FIXED ✓
**Problem:** `_ср._ <Etiopio>` создавал группу с единственным элементом `'<'`
**Solution:** 
1. Enhanced `_is_pure_reference_segment()` to filter `;` and `.` punctuation
2. Added `_strip_reference_suffix()` to remove `_ср._ <...>` from line endings in `_apply_source_fallback()`
3. Added filtering in `_extract_translation_from_explanation()` to skip pure reference text nodes like `<Etiopio>.`
**Test:** 
- Article 52: Now has 1 group (was 2), no ghost `'<'` group
- Article 270: Still 25 groups, section `[~um/i]` has 2 translations (no ghost `<ventumi>` reference)
**Location:** `translation_review.py` lines 1327-1362, 1091-1092, 1855-1860

### Issue #7: "Как в источнике" candidate - FIXED ✓
**Problem:** Кандидат "Как в источнике" показывал раскрытые варианты (с раскрытыми скобками), должен показывать простой split по `,` и `;`
**Solution:**
1. Added `_split_inline_synonyms_simple()` - splits by commas WITHOUT expanding parentheses
2. Changed `base_clean` processing to use `_split_inline_synonyms_simple()` instead of `_expand_inline_synonyms_list()`
3. `expanded_clean` still uses full expansion with `_expand_inline_synonyms_list()`
**Test:**
- Article 39 `[~i]`: "Как в источнике" shows `['аберр\`ировать', 'дав\`ать аберр\`ацию']` (simple split)
- Article 39 numbered value 2: base_items = `['аберр\`ация', 'отклон\`ение']` WITHOUT `(от нормы)` expansion
- Article 270: 25 groups, no regressions
**Location:** `translation_review.py` lines 1041-1053 (new function), 824-827 (usage)

### Issue #10: Reference-only articles creating empty groups - FIXED ✓
**Problem:** Articles containing only references (e.g., `1. _см._ <malagnoski>; 2. _см._ <forjxuri>`) created empty groups with content like `['1']` (numbered value only)
**Solution:**
1. Added `_is_reference_only_block()` function to detect blocks with only references
2. Checks that content contains only digits/dividers and all children are reference/explanation nodes
3. Skip such blocks before processing in `_collect_groups_from_blocks()`
**Test:**
- Article 55: Now has 0 groups (was 1 with `['1']`)
- Article 270: Still 25 groups, no regressions
- Article 383: 48 groups (unchanged from previous fixes)
**Location:** `translation_review.py` lines 321-352 (new function), 462-464 (usage)

### Issue #4: Tilde examples filtering - FIXED ✓
**Problem:** Examples with tilde (Esperanto text) mixed with translations, e.g., `"`улей ~ujo"`, `"`улей natura ~ujo"` in article 23, or broken references like `"см.tifoido"` in article 19
**Solution:**
1. Enhanced `_is_meaningful_item()` to filter items containing `~` (tilde marker for Esperanto examples)
2. Added filtering for broken references starting with `"см."` or `"ср."` without proper spacing
3. Added check in `_collect_groups_from_blocks()` to skip groups with no meaningful items after filtering
**Test:**
- Article 23 `[~uj/o]`: Now has 0 groups (was 1 with tilde text), total 11 groups (was 12)
- Article 19: Group `~a tifo` now has `['tifoida febro']` only (filtered out `'см.tifoido'`), 8 groups total
- Article 270: Still 25 groups, no regressions
- Article 383: Still 48 groups, no regressions
**Location:** `translation_review.py` lines 2440-2447 (_is_meaningful_item), 288-293 (group filtering)
**Note:** This is a post-processing fix. Root cause is in parser concatenating tilde text with translations. Full fix would require parser changes in templates.py.

### Issue #1: Grave accent word merging - FIXED ✓
**Problem:** `(\`имя) прилаг\`ательное` → `\`имяприлаг\`ательное` (space lost between words with grave accents)
**Root Cause:** Function `_compress_optional_prefix_spacing()` was designed to remove spaces after short optional prefixes like `(воз)действие`, but incorrectly applied to grave-marked words. The function checks if optional parts are ≤4 characters; `\`имя` is 4 characters and qualified for space removal.
**Solution:** Added check in `_should_collapse()` to preserve spaces when grave accents (backticks) are present:
```python
def _should_collapse(candidate: str) -> bool:
    if not candidate:
        return False
    # Don't collapse if contains grave accent - stress marks need space preserved  
    if "`" in candidate:
        return False
    # ... rest of checks
```
**Test:**
- Article 2: Now shows `['прилагательное', '\`имя прилагательное']` WITH space ✓
- Article 270: Still 25 groups (no regression) ✓
- Article 383: Still 48 groups (no regression) ✓
**Location:** `translation_review.py` lines 2491-2493 (_should_collapse in _compress_optional_prefix_spacing)
**Credit:** Fixed by second Droid instance in focused debugging session

### Issue #6: Optional parts after words - PARTIALLY FIXED ⚠️
**Problem:** `отклонение (от нормы)` lost closing parenthesis, becoming `отклонение (от нормы` (article 39)
**Solution implemented:**
1. Fixed `_strip_trailing_punctuation()` to preserve balanced parentheses (lines 2399-2416)
   - Only strips trailing `)` if parentheses are unbalanced
   - Preserves balanced pairs like `"слово (пояснение)"`
2. Enhanced `_expand_parenthetical_forms()` to generate BOTH variants for complex optional parts (lines 2101-2119)
   - When optional part has spaces/commas inside (e.g., `(от нормы)`), now returns both: `['отклонение', 'отклонение (от нормы)']`
   - Previously only returned variant WITH parentheses
**Test:**
- Article 270: Still 25 groups (no regressions)
- Article 383: Still 48 groups (no regressions)
- Article 39: Closing parenthesis no longer lost ✓
**Status:** Parentheses preservation works, BUT candidate generation needs additional work to properly show expanded variants in UI
**Location:** `translation_review.py` lines 2399-2416 (_strip_trailing_punctuation), 2101-2119 (_expand_parenthetical_forms)

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
