# Hypothesis graph: matplotlib__matplotlib-22719

## H₀: Initial diagnosis (abduction, 85%)

**Node type**: abduction  
**Status**: active  
**Timestamp**: 2026-05-23

### Hypothesis
The test `test_no_deprecation_on_empty_data` fails because `StrCategoryConverter.convert()` incorrectly identifies empty arrays as "numlike" and triggers a deprecation warning.

### Root cause
In `lib/matplotlib/category.py:58-60`, the code checks:
```python
is_numlike = all(units.ConversionInterface.is_numlike(v)
                 and not isinstance(v, (str, bytes))
                 for v in values)
```

Python's `all()` function returns `True` for empty sequences. When `values` is an empty array (from `ax.plot([], [])`), the generator produces no elements, so `all()` returns `True`, incorrectly marking the empty array as "numlike".

### Evidence
1. Test failure shows: `ConversionError: Failed to convert value(s) to axis units: array([], dtype=float64)`
2. Verified with `python -c "print(all(x > 0 for x in []))"` → returns `True`
3. Git history (commit 90f2e4cf49) shows this deprecation warning was added in version 3.5

### Edit sites
- `lib/matplotlib/category.py` lines 56-67: Add early return for empty arrays before the `is_numlike` check
  - After line 56 (`values = np.atleast_1d(np.array(value, dtype=object))`), check if `len(values) == 0`
  - If empty, return `np.asarray(values, dtype=float)` directly without the deprecation warning

### Confidence
85% - This is an abduction based on:
- Clear code path from test to failure
- Verified Python `all()` behavior on empty sequences
- No competing explanations identified

## Gate Loop: /craft

### Iteration 1: Draft & Volley

**Drafted Fix:** Early return for empty arrays before `is_numlike` check.

**codex Critique:** Fix too broad — skips `unit.update(values)` and changes categorical path. Better: fix the vacuous truth with `bool(values.size) and all(...)`.

**Applied Fix:**
```python
is_numlike = bool(values.size) and all(
    units.ConversionInterface.is_numlike(v)
    and not isinstance(v, (str, bytes))
    for v in values)
```

**Gate Result:** ✅ PASS — `test_no_deprecation_on_empty_data` passes. 90 passed, 8 xfailed (expected).

**Edit Site:** `lib/matplotlib/category.py:58-61` — Added `bool(values.size) and` before `all()` to prevent vacuous truth on empty arrays.

**Resolution:** The narrower fix prevents empty arrays from being misclassified as numlike while preserving the normal categorical conversion path. Gate green on first iteration.

## Audit: matplotlib__matplotlib-22719

### Patch verification
Patch is live: `lib/matplotlib/category.py` modified (4 insertions, 3 deletions)

### FAIL_TO_PASS
- `test_no_deprecation_on_empty_data`: **PASS** ✓

### PASS_TO_PASS regressions
None — all 89 PASS_TO_PASS tests remain passing.

### Pre-existing failures
None — 8 xfailed tests are expected failures (xfail markers), not regressions.

### Gate output
```
90 passed, 8 xfailed, 1 warning in 1.15s
```

All FAIL_TO_PASS tests now pass. Zero PASS_TO_PASS regressions. Full contract satisfied.

### Applied patch
```diff
diff --git a/lib/matplotlib/category.py b/lib/matplotlib/category.py
index c823b68fd9..04dc0c59c3 100644
--- a/lib/matplotlib/category.py
+++ b/lib/matplotlib/category.py
@@ -55,9 +55,10 @@ class StrCategoryConverter(units.ConversionInterface):
         values = np.atleast_1d(np.array(value, dtype=object))
         # pass through sequence of non binary numbers
         with _api.suppress_matplotlib_deprecation_warning():
-            is_numlike = all(units.ConversionInterface.is_numlike(v)
-                             and not isinstance(v, (str, bytes))
-                             for v in values)
+            is_numlike = bool(values.size) and all(
+                units.ConversionInterface.is_numlike(v)
+                and not isinstance(v, (str, bytes))
+                for v in values)
         if is_numlike:
             _api.warn_deprecated(
                 "3.5", message="Support for passing numbers through unit "
```

The fix adds `bool(values.size) and` to prevent `all()` from returning True on empty arrays (vacuous truth), correctly handling the empty data case without triggering the deprecation warning.

VERDICT: RESOLVED
RE-ENTER: none
