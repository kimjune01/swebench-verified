# Hypothesis graph: pydata__xarray-4075

## H₀: Initial abduction (recon r0)

**Status:** Active hypothesis  
**Type:** Abduction  
**Confidence:** 95% (deduction from code trace)

### Hypothesis

Boolean weights cause incorrect sum_of_weights calculation because `xr.dot()` of two boolean arrays returns a boolean scalar instead of numeric sum.

### Evidence

1. Test failure: `test_weighted_sum_of_weights_bool`
   - Input: `da=[1,2]`, `weights=[True, True]`
   - Expected: `2`
   - Actual: `1.0`

2. Test failure: `test_weighted_mean_bool`
   - Input: `da=[1,1]`, `weights=[True, True]`
   - Expected: `1`
   - Actual: `2.0`

3. Code trace in `xarray/core/weighted.py`:
   - `_sum_of_weights` (line 145): calls `self._reduce(mask, self.weights, dim=dim, skipna=False)`
   - `mask = da.notnull()` returns boolean array
   - `self.weights` is boolean `[True, True]`
   - `_reduce` (line 135): calls `dot(da, weights, dims=dim)`
   - When both inputs are boolean, dot returns boolean instead of numeric sum

### Root cause location

File: `xarray/core/weighted.py`  
Method: `Weighted._reduce` (lines 113-135)  
Line: 135 - `return dot(da, weights, dims=dim)`

### Fix specification

Before calling `dot()`, convert boolean arrays to int:

```python
# After line 130 (after the skipna/fillna logic):
if da.dtype.kind == 'b':
    da = da.astype(int)
if weights.dtype.kind == 'b':
    weights = weights.astype(int)
```

This ensures dot product returns numeric result when either or both inputs are boolean.

### Why this location

- `_reduce` is called by both `_sum_of_weights` (with boolean mask) and `_weighted_sum` (with numeric data)
- Converting in `_reduce` handles all cases in one place
- Conversion must happen after skipna/fillna logic (line 129-130) since boolean arrays don't have NaN
- Must happen before `dot()` call (line 135)


## Craft: Gate Loop

### Iteration 1 - Initial Fix

**Hypothesis**: Convert boolean arrays to int before `dot()` call in `_reduce()` method.

**Implementation**: Added boolean-to-int conversion in `xarray/core/weighted.py` at line 135 (before the `return dot(da, weights, dims=dim)` statement):
```python
# convert boolean arrays to int for dot product to return numeric sums
if da.dtype.kind == "b":
    da = da.astype(int)
if weights.dtype.kind == "b":
    weights = weights.astype(int)
```

**Codex review**: Suggested using specific numpy dtype instead of bare `int`, noted fix might be broad but acceptable. Main concern was platform-dependent casting, but `int` is sufficient for boolean conversion.

**Gate result**: ✅ PASSED - All 960 tests passed including both FAIL_TO_PASS tests:
- `test_weighted_sum_of_weights_bool`
- `test_weighted_mean_bool`

**E-value**: Convergent (green) - First attempt successful.

**Conclusion**: Fix correctly addresses the root cause. Boolean arrays are now converted to int before the dot product, ensuring numeric sums instead of boolean results.

## Audit: pydata__xarray-4075

### FAIL_TO_PASS
- xarray/tests/test_weighted.py::test_weighted_sum_of_weights_bool: ✅ PASSED
- xarray/tests/test_weighted.py::test_weighted_mean_bool: ✅ PASSED

### PASS_TO_PASS regressions
None. Gate completed with 960 passed, 0 failed, 2 xfailed (expected failures).

### Pre-existing (not counted, confirmed against base capture)
- xarray/tests/test_weighted.py::test_weighted_operations_keep_attr_da_in_ds[sum] - XFAIL (known issue GH: 3595)
- xarray/tests/test_weighted.py::test_weighted_operations_keep_attr_da_in_ds[mean] - XFAIL (known issue GH: 3595)

### Patch summary
```diff
diff --git a/xarray/core/weighted.py b/xarray/core/weighted.py
index 996d2e4c..facae5db 100644
--- a/xarray/core/weighted.py
+++ b/xarray/core/weighted.py
@@ -132,6 +132,12 @@ class Weighted:
         # `dot` does not broadcast arrays, so this avoids creating a large
         # DataArray (if `weights` has additional dimensions)
         # maybe add fasttrack (`(da * weights).sum(dims=dim, skipna=skipna)`)
+
+        # convert boolean arrays to int for dot product to return numeric sums
+        if da.dtype.kind == "b":
+            da = da.astype(int)
+        if weights.dtype.kind == "b":
+            weights = weights.astype(int)
         return dot(da, weights, dims=dim)
```

The fix correctly converts boolean arrays to int before the dot product operation in `Weighted._reduce()`, ensuring numeric sums are returned instead of boolean scalars. This resolves both failing tests with no regressions across the full test suite.

