# TASK: Fix Issue #1 - Grave Accent Word Merging

## Your Mission

Fix the bug where `(\`имя) прилаг\`ательное` becomes `\`имяприлаг\`ательное` (space lost).

Expected result: `\`имя прилагательное` (WITH space between words)

## Setup

1. Read `Agents.ISSUE1_FOCUSED.md` - contains all context you need
2. Working directory: `/home/avo/rueo_global`
3. Use `PYTHONPATH=backend` for all Python scripts

## Your Workflow

### Phase 1: Locate the Bug (30-60 min)

Use the debugging helpers from Agents.ISSUE1_FOCUSED.md to:

1. **Verify the problem exists:**
   ```bash
   # Check article 2 current state
   [use CLI helper from focused doc]
   ```

2. **Add DEBUG output** in `backend/app/services/translation_review.py`:
   - In `_split_translation_groups()` after line 836, 838, 839, 840
   - Track where space disappears
   - Example:
     ```python
     import sys
     print(f"DEBUG line 838: {expanded}", file=sys.stderr)
     ```

3. **Test suspect functions individually:**
   - `_expand_cross_product(['прилаг\`ательное', '\`имя прилаг\`ательное'])`
   - `_expand_suffix_appending([...])`
   - See which one loses the space

### Phase 2: Fix (30-60 min)

Once you find where space is lost:

1. **Understand WHY** it's being removed
2. **Fix the logic** to preserve spaces with grave accents
3. **Test the fix:**
   ```bash
   # Reparse article 2
   [use CLI helper]
   ```

4. **Verify no regressions:**
   ```bash
   # Test articles 270, 383
   [use CLI helpers]
   ```

### Phase 3: Clean Up (15 min)

1. **Remove DEBUG output** (all `print(..., file=sys.stderr)` lines)
2. **Verify code compiles:**
   ```bash
   PYTHONPATH=backend python -m compileall backend/app/services/translation_review.py
   ```
3. **Document your findings** in brief comment at fix location

## Success Criteria

✅ Article 2 shows: `['прилагательное', '`имя прилагательное']` (WITH space)
✅ Article 270: 25 groups (unchanged)
✅ Article 383: 48 groups (unchanged)
✅ No DEBUG output left in code
✅ Code compiles without errors

## Deliverables

Report back with:

1. **Root cause:** Where and why space was lost (1-2 sentences)
2. **Fix applied:** What you changed (code snippet + line numbers)
3. **Test results:** Article 2, 270, 383 group counts
4. **Files modified:** List of changed files

## Important Notes

- **DO NOT** modify `Agents.md` or `Agents.FULL_HISTORY.md`
- **DO NOT** commit changes (manager will do it)
- **DO** use the CLI helpers extensively - they're ready to use
- **DO** think systematically - add DEBUG, test, iterate

## Estimated Time: 1.5-2 hours

Good luck! This is the toughest bug in the parser, but we've narrowed it down significantly.
