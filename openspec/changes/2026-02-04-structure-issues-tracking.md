# 2026-02-04: Structure issues tracking and exclusion fixes

## Problem

The `tracking-summary.json` file generated during dictionary import was not storing information about detected structural issues in source files. This made it impossible to review issues after import without re-running the full process.

Additionally, `VortaroER-daily/w.txt` (Esperanto) has expected structural patterns that were being reported as errors every run:
- Headers followed by `\head\` lines (section headers)
- Headers followed by `\p\` lines (paragraph markers)
These are not real issues but legitimate dictionary markup.

## Changes

### 1. Enhanced `backend/app/importer.py`

**Added structure issue tracking:**
- New `STRUCTURE_ISSUE_EXCEPTIONS` dict to exclude files with expected patterns (e.g., `w.txt` for Esperanto)
- Modified `_detect_structure_issues()` to support exception filtering
- Updated `_process_language()` to filter out issues from excluded files
- Modified `_write_status_file()` to always write `structure_issues` to `tracking-summary.json` with detailed information:
  - `total`: count of issues
  - `files_with_issues`: number of affected files
  - `files`: dict mapping filenames to issue counts
  - `details`: list of specific issues (line, word, context)

**Example tracking-summary.json format:**
```json
{
  "ru": {
    "tracking": { ... },
    "structure_issues": {
      "total": 1,
      "files_with_issues": 1,
      "files": {
        "VortaroRE-daily/16_p.txt": 1
      },
      "details": [
        {
          "file": "VortaroRE-daily/16_p.txt",
          "line": 41814,
          "type": "word_without_header",
          "word": "[промышл`ять]",
          "context": "Заголовок '2026-02-02 13:00 bk№' не соответствует формату"
        }
      ]
    }
  }
}
```

### 2. Created `scripts/check_structure_issues.py`

New standalone script to check structural issues without running full import:
- Validates `VortaroRE-daily/*.txt` and `VortaroER-daily/*.txt` files
- Same detection logic as `importer.py` (via `_detect_structure_issues()`)
- Supports `STRUCTURE_ISSUE_EXCEPTIONS` (excludes `w.txt`)
- Multiple output formats:
  - Human-readable (default with `-v` for verbose)
  - JSON (`--json`)
  - Tracking-summary format (`--tracking-format`)

**Usage:**
```bash
# Quick check (both languages)
python3 scripts/check_structure_issues.py

# Verbose details
python3 scripts/check_structure_issues.py -v

# JSON output
python3 scripts/check_structure_issues.py --json

# Tracking-summary format (for merging)
python3 scripts/check_structure_issues.py --tracking-format

# Single language
python3 scripts/check_structure_issues.py --lang ru -v
```

## Files modified

- `backend/app/importer.py`:
  - Added `STRUCTURE_ISSUE_EXCEPTIONS` constant
  - Updated `_detect_structure_issues()` signature
  - Modified `_process_language()` to filter exceptions
  - Updated `_write_status_file()` to include structure_issues

## Files added

- `scripts/check_structure_issues.py` - Standalone structure checker

## Verification

1. Run structure checker:
   ```bash
   cd ~/rueo_master
   python3 scripts/check_structure_issues.py -v
   ```
   Expected: `w.txt` issues excluded, real issues reported

2. Import dictionary and check `tracking-summary.json`:
   ```bash
   ~/rueo_master/scripts/rueo_update.sh run --last-ru-letter "предштормовой"
   cat ~/rueo_master/backend/data/tekstoj/tracking-summary.json
   ```
   Expected: `structure_issues` sections present in both `eo` and `ru` blocks

## Backport to Stage II

This change should be applied to `feature/Stage_II`:
- The `check_structure_issues.py` script is useful for all stages
- Structure issue tracking is valuable for parser development in Stage II
- Exceptions list may need adjustment based on Stage II patterns

## Notes

- Manual fix applied to `VortaroRE-daily/16_p.txt`: header `2026-02-02 13:00 bk№` → `2026-02-02 13:00 bk#`
- Article `[промышл`ять]` already has correct header in database
- Next import will not report issues from `16_p.txt` or `w.txt`
