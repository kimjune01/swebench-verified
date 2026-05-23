# Hypothesis graph: django__django-13670

## Hypothesis H₀ (abduction → deduction)

**Node:** dateformat.y() string slicing bug
**Type:** Root cause
**Confidence:** 99% (deduction)

**Observation:** The failing tests show that `dateformat.format(datetime(year, 9, 8, 5, 0), 'y')` produces:
- Year 476: '6' instead of '76'
- Year 42: '' instead of '42'
- Year 4: '' instead of '04'

**Root cause:** The `y()` method in `django/utils/dateformat.py:329` uses string slicing `str(self.data.year)[2:]` to extract the last two digits of the year. This fails for years < 100 because:
- Year 476: str(476) = '476', [2:] = '6' (takes only the last digit)
- Year 42: str(42) = '42', [2:] = '' (nothing after index 2)
- Year 4: str(4) = '4', [2:] = '' (nothing after index 2)

**Supporting evidence:**
- `django/utils/dateformat.py:329` — `return str(self.data.year)[2:]`
- Python's strftime('%y') correctly produces '76', '42', '04' for these years using modulo 100 arithmetic
- PHP date('y') also uses modulo 100 (as stated in the problem description)

**Required fix:** Replace string slicing with modulo arithmetic and zero-padding:
```python
return '%02d' % (self.data.year % 100)
```

This ensures the last two digits are extracted mathematically (not by string position) and formatted with leading zeros.

**Edit sites:**
- `django/utils/dateformat.py` line 329: Change `return str(self.data.year)[2:]` to `return '%02d' % (self.data.year % 100)`

**Verification:** Python's strftime behavior confirms this is correct:
- datetime(476, 9, 8, 5, 0).strftime('%y') → '76'
- datetime(42, 9, 8, 5, 0).strftime('%y') → '42'
- datetime(4, 9, 8, 5, 0).strftime('%y') → '04'


## Craft gate-loop iteration 1

**Change applied:**
- `django/utils/dateformat.py:329` — replaced `return str(self.data.year)[2:]` with `return '%02d' % (self.data.year % 100)`

**Gate result:** ✅ PASS

All 18 tests passed, including `test_year_before_1000` which now correctly produces:
- Year 476 → '76' (was '6')
- Year 42 → '42' (was '')
- Year 4 → '04' (was '')

The fix uses modulo 100 arithmetic to mathematically extract the last two digits and formats with `%02d` to ensure leading zeros, matching Python's `strftime('%y')` and PHP's `date('y')` behavior.

---

# Audit: django__django-13670

## FAIL_TO_PASS
- test_year_before_1000 (utils_tests.test_dateformat.DateFormatTests): PASS ✓

## PASS_TO_PASS regressions
none

## Pre-existing (not counted, confirmed against base capture)
none

## Classification

Patch is live:
```
django/utils/dateformat.py | 2 +-
1 file changed, 1 insertion(+), 1 deletion(-)
```

Gate output: All 18 tests passed.

The FAIL_TO_PASS test `test_year_before_1000` now passes. All PASS_TO_PASS tests continue to pass. No regressions introduced.

VERDICT: RESOLVED
RE-ENTER: none
