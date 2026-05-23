# Hypothesis graph: django__django-14539

## H1: Root Cause - Incorrect trail calculation in trim_punctuation (Deduction, 99%)

**Location**: `django/utils/html.py`, line 288 in `trim_punctuation` function

**Problem**: When trimming trailing punctuation from URLs containing HTML entities (like `&lt`), the function calculates the `trail` by slicing the escaped string at a position derived from the unescaped string's length. This causes incorrect slicing when HTML entities are present, because entities have different lengths in escaped vs unescaped form.

**Code path**:
1. `urlize()` calls `trim_punctuation()` with `middle="google.com/?q=1&lt!"`
2. Line 283: `middle_unescaped = html.unescape(middle)` → `"google.com/?q=1<!"`
3. Line 284: `stripped = middle_unescaped.rstrip(TRAILING_PUNCTUATION_CHARS)` → `"google.com/?q=1<"`
4. Line 288: **BUG** `trail = middle[len(stripped):] + trail`
   - `len(stripped)` = 16 (unescaped length)
   - `middle[16:]` = `"lt!"` (wrong - indexes into escaped string with unescaped position)
   - Should be: `"!"` (just the trailing punctuation)

**Why this happens**: `&lt` is 3 characters in escaped form but `<` is 1 character unescaped. When we use `len(stripped)` (16, measured on unescaped) to index into `middle` (escaped), we land in the middle of the `&lt` entity at position 16, which is the `l` in `&lt`.

**Fix**: Calculate how many characters were removed from the unescaped string (`len(middle_unescaped) - len(stripped)`), then remove that many characters from the END of the escaped string, rather than slicing at a position.

**Evidence**:
- `django/utils/html.py:288` - `trail = middle[len(stripped):] + trail`
- Test expects: link text `google.com/?q=1&lt`, trail `!`
- Test gets: link text `google.com/?q=1&lt`, trail `lt!`

**Historical context**: Commit 8d76443aba (2019) changed from custom `unescape()` to `html.unescape()`. The old function only handled entities with semicolons (`&lt;`), while `html.unescape()` also handles entities without semicolons (`&lt`). This exposed the latent bug in the slicing logic.


## Craft gate loop

### Iteration 1: Initial fix applied

**Change**: Modified `trim_punctuation()` in `django/utils/html.py` lines 287-291
- Replaced buggy calculation that sliced escaped string using unescaped string length
- New approach: calculate `removed_len` from unescaped strings, then slice escaped string from the end

**Diff**:
```python
# Old (buggy):
trail = middle[len(stripped):] + trail
middle = middle[:len(stripped) - len(middle_unescaped)]

# New (fixed):
removed_len = len(middle_unescaped) - len(stripped)
trail = middle[-removed_len:] + trail
middle = middle[:-removed_len]
```

**Gate result**: ✅ PASS

All 16 tests passed, including both FAIL_TO_PASS tests:
- `test_urlize` - correctly handles `&lt` entity with trailing `!`
- `test_urlize_unchanged_inputs` - no regressions on edge cases

**Resolution**: The recon diagnosis was correct. The fix properly handles HTML entities by counting removed characters in the unescaped string, then removing the same count from the END of the escaped string, preserving entity integrity.

---

# Audit: django__django-14539

## FAIL_TO_PASS
- test_urlize (utils_tests.test_html.TestUtilsHtml): PASS ✓
- test_urlize_unchanged_inputs (utils_tests.test_html.TestUtilsHtml): PASS ✓

## PASS_TO_PASS regressions
none

## Pre-existing (not counted, confirmed against base capture)
none

## Gate output
All 16 tests passed. The craft patch successfully fixed the urlize function to properly stop URL detection at HTML entity boundaries like `&lt`, preventing false matches that included the entity text.

VERDICT: RESOLVED
RE-ENTER: none
