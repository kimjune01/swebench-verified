# Hypothesis graph: pydata__xarray-3151

## H₀: Monotonicity check applied to all dimensions instead of only concat_dims
**Mode**: deduction  
**Confidence**: 95%

### Evidence
The failing test creates two datasets with:
- ds1: x=[1,2,3], y=['a','c','b']
- ds2: x=[4,5,6,7], y=['a','c','b']

The x dimension varies between datasets (should be concatenated), while y is identical in both (bystander dimension).

Error trace shows: `ValueError: Resulting object does not have monotonic global indexes along dimension y` raised at xarray/core/combine.py:509.

### Code analysis

`_infer_concat_order_from_coords` (lines 51-115) correctly identifies concat dimensions:
- Lines 69-72: If coordinates are identical across datasets, dimension is NOT added to concat_dims (it's a bystander)
- Only dimensions that vary are added to concat_dims

`combine_by_coords` (lines 393-517):
- Line 493: Gets concat_dims from _infer_concat_order_from_coords
- Line 499: Calls _combine_nd to concatenate along concat_dims only
- Lines 503-509: **BUG** - Checks monotonicity for ALL dimensions, not just concat_dims:

```python
# Check the overall coordinates are monotonically increasing
for dim in concatenated.dims:  # <-- WRONG: iterates ALL dims
    if dim in concatenated:
        indexes = concatenated.indexes.get(dim)
        if not (indexes.is_monotonic_increasing
                or indexes.is_monotonic_decreasing):
            raise ValueError("Resulting object does not have monotonic"
                             " global indexes along dimension {}"
                             .format(dim))
```

Documentation at line 405-406 states: "Non-coordinate dimensions will be ignored, as will any coordinate dimensions which do not vary between each dataset."

### Root cause
The monotonicity check at line 503 iterates over `concatenated.dims` (all dimensions) instead of `concat_dims` (only dimensions that were concatenated). Bystander dimensions with identical non-monotonic coordinates incorrectly trigger the ValueError.

### Fix specification
Change line 503 in xarray/core/combine.py from:
```python
for dim in concatenated.dims:
```
to:
```python
for dim in concat_dims:
```

This ensures only concatenated dimensions are checked for monotonicity, matching the documented behavior.


---
## Craft: Gate loop iteration 1

**Drafted fix:**
```diff
--- a/xarray/core/combine.py
+++ b/xarray/core/combine.py
@@ -503,7 +503,7 @@ def combine_by_coords(datasets, compat='no_conflicts', data_vars='all',
                                    fill_value=fill_value)
 
         # Check the overall coordinates are monotonically increasing
-        for dim in concatenated.dims:
+        for dim in concat_dims:
             if dim in concatenated:
                 indexes = concatenated.indexes.get(dim)
                 if not (indexes.is_monotonic_increasing
```

**Codex review:** Patch is directionally correct. No functional issues. Correctly targets the bug - monotonicity should only be enforced for dimensions used to concatenate datasets, not identical bystander dimensions. The test already exists in the test suite.

**Gate outcome:** PASS
- All 67 tests passed
- FAIL_TO_PASS test `test_combine_leaving_bystander_dimensions` now passes
- No regressions

**Resolution:** The one-line fix correctly restricts monotonicity validation to only concatenated dimensions (`concat_dims`), excluding bystander dimensions with identical coordinates across datasets.

---
## Audit: pydata__xarray-3151

### Phase 1: Patch verification
```
 xarray/core/combine.py | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```
Patch is live. Changed line 504 from `for dim in concatenated.dims:` to `for dim in concat_dims:`.

### Phase 2: Gate execution
```
67 passed, 1 xfailed, 40 warnings in 1.77s
```

### Phase 3: Classification

#### FAIL_TO_PASS
- `xarray/tests/test_combine.py::TestCombineAuto::test_combine_leaving_bystander_dimensions`: **PASS** ✓

#### PASS_TO_PASS regressions
None. All 67 tests passed, matching or exceeding baseline expectations.

#### Pre-existing failures (not counted)
The xfailed test `TestManualCombine::test_manual_concat_too_many_dims_at_once` is a pre-existing expected failure, not in scope for this fix.

### Phase 4: Verdict

**Contract fulfilled:**
- ✓ All FAIL_TO_PASS tests now pass (1/1)
- ✓ Zero PASS_TO_PASS regressions (0)

The patch correctly fixes the bug by restricting monotonicity validation to only dimensions that were actually concatenated, not all dimensions including bystanders with identical coordinates.

VERDICT: RESOLVED
RE-ENTER: none
