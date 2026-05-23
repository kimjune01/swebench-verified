# Hypothesis graph: django__django-11848

## Hypothesis H0 (Initial Diagnosis) - Abduction - 95%

**Status**: Active  
**Timestamp**: 2026-05-22 (recon phase 1)  
**Reasoning Mode**: Deduction (traced code, read test expectations, verified against RFC 7231 quote)

### Observation
Tests fail when parsing RFC 850 dates with two-digit years. Specifically:
- `test_parsing_rfc850` fails on subtest `'Wednesday, 31-Dec-70 08:49:37 GMT'` with current year = 2020
- Expected: `datetime(2070, 12, 31, 8, 49, 37)`
- Actual: `datetime(1970, 12, 31, 8, 49, 37)`

### Root Cause
`django/utils/http.py` lines 178-182 implement hardcoded two-digit year logic:
```python
if year < 100:
    if year < 70:
        year += 2000
    else:
        year += 1900
```

This violates RFC 7231 which states: "Recipients of a timestamp value in rfc850-date format, which uses a two-digit year, MUST interpret a timestamp that appears to be more than 50 years in the future as representing the most recent year in the past that had the same last two digits."

The current code always treats 0-69 as 2000-2069 and 70-99 as 1970-1999, regardless of the current year.

### Correct Behavior
Per RFC 7231:
1. Calculate candidate year = 2000 + two_digit_year
2. If (candidate_year - current_year) > 50, use 1900 + two_digit_year instead
3. Otherwise use candidate_year

Test case validation:
- 2019 + "69" → 2069 (50 years ahead, acceptable) ✓
- 2019 + "70" → 1970 (2070 would be 51 years, too far) ✓
- 2020 + "70" → 2070 (50 years ahead, acceptable) ✓
- 2020 + "71" → 1971 (2071 would be 51 years, too far) ✓
- 2048 + "00" → 2000 (2100 would be 52 years, too far) ✓
- 2048 + "99" → 1999 (2099 would be 51 years, too far) ✓

### Edit Sites
**Single location**: `django/utils/http.py:178-182`

Replace hardcoded logic with RFC-compliant calculation:
```python
if year < 100:
    current_year = datetime.datetime.utcnow().year
    candidate_year = 2000 + year
    if candidate_year - current_year > 50:
        year = 1900 + year
    else:
        year = candidate_year
```

### Supporting Evidence
- File: `django/utils/http.py:178-182` — hardcoded year < 70 check
- File: `tests/utils_tests/test_http.py:330-345` — comprehensive test cases covering edge cases at 50-year boundary
- Only occurrence: grep confirms this is the sole location of "year < 70" logic in Django codebase (excluding tests)

### Confidence
**Deduction - 95%**  
Code path is straightforward, RFC requirement is explicit, test cases comprehensively cover the expected behavior. The only uncertainty (5%) is whether there are edge cases around leap years or year boundaries not covered by the tests, but the core logic is unambiguous.


## Gate Loop - Iteration 1

**Applied fix:** Replaced hardcoded year thresholds (1900/2000) with RFC 7231 compliant current-century logic in `django/utils/http.py:178-184`.

**Changes:**
```python
if year < 100:
    current_year = datetime.datetime.utcnow().year
    current_century = current_year - (current_year % 100)
    if year - (current_year % 100) > 50:
        year += current_century - 100
    else:
        year += current_century
```

**codex volley:** Caught critical bug in initial draft that hardcoded 1900/2000 (would break after century rollover). Revised to use dynamic current-century calculation.

**Gate result:** ✅ PASS - All 45 tests pass including both FAIL_TO_PASS:
- test_parsing_rfc850 ... ok
- test_parsing_year_less_than_70 ... ok

**Trajectory:** Convergent success (green gate on first iteration after codex review)


## Audit: django__django-11848

### Patch Confirmation
✅ Patch is live: `django/utils/http.py | 8 +++++---`

### FAIL_TO_PASS Results
- `test_parsing_rfc850` - **PASS** ✓ (was FAIL on base)
- `test_parsing_year_less_than_70` - **PASS** ✓ (was ok on base)

### PASS_TO_PASS Regressions
**None** - All 43 PASS_TO_PASS tests remain passing.

### Pre-existing Failures (not counted)
**None** - The fail-on-base capture showed `test_parsing_rfc850` failing on base (expected), which is now fixed.

### Gate Output Summary
All 45 tests passed:
- Both FAIL_TO_PASS tests now pass
- All PASS_TO_PASS tests remain green
- No regressions introduced
- Clean gate: `Ran 45 tests in 0.003s OK`

### Verdict Analysis
The patch successfully implements RFC 7231 compliant two-digit year parsing:
- Replaced hardcoded 70-year threshold with dynamic current-year calculation
- Uses current century ± 100 based on 50-year boundary check
- All edge cases validated by comprehensive test suite

**VERDICT: RESOLVED**  
**RE-ENTER: none**
