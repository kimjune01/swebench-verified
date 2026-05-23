# Hypothesis graph: pydata__xarray-4356
# Hypothesis Graph: pydata__xarray-4356

## H₀: Initial Observation (Abduction)
**Status**: CONFIRMED  
**Type**: Abduction  
**Timestamp**: Initial recon pass

The tests fail because `_maybe_null_out` in `xarray/core/nanops.py:28-31` explicitly raises a ValueError when `axis` is a tuple or list, preventing multi-dimensional reduction with `min_count`.

**Evidence**:
- Test failure traceback shows: `ValueError: min_count is not available for reduction with more than one dimensions.`
- Error originates from `xarray/core/nanops.py:30`
- The check `if hasattr(axis, "__len__")` detects tuple/list axis and immediately raises

**Call path**: 
- `da.sum(dim=["x", "y", "z"], min_count=3)` 
- → `xarray/core/common.py:46` 
- → `xarray/core/dataarray.py:2347` 
- → `xarray/core/variable.py:1640` 
- → `xarray/core/duck_array_ops.py:335` 
- → `xarray/core/nanops.py:115` (`nansum`)
- → `xarray/core/nanops.py:30` (`_maybe_null_out` ValueError)

## H₁: Root Cause (Deduction)
**Status**: ACTIVE  
**Type**: Deduction  
**Confidence**: 98%

The root cause is a deliberate but incomplete implementation in `_maybe_null_out`:
1. Lines 28-31 block multi-dimensional reduction entirely
2. Line 35 uses `mask.shape[axis]` which only works for single-int axis (not tuple)

When `axis` is a tuple like `(0, 1, 2)`, `mask.shape[axis]` would fail with TypeError because you can't index a tuple with a tuple. The ValueError at lines 28-31 was added as a guard against this unimplemented case.

**Supporting evidence**:
- `xarray/core/nanops.py:35`: `null_mask = (mask.shape[axis] - mask.sum(axis) - min_count) < 0`
- `mask.shape[axis]` is syntactically invalid when axis is a tuple
- `mask.sum(axis)` already handles tuple axes correctly (numpy feature)
- Git history shows this ValueError has existed since the function was created
- The test expects: `da.sum(dim=["x","y","z"], min_count=3)` == `da.sum(dim=..., min_count=3)` (reducing all dimensions should work the same way)

**Why the fix works**:
- Replace `mask.shape[axis]` with `np.prod(np.take(mask.shape, axis))`
- This handles both single-axis and multi-axis cases uniformly:
  - Single: `np.prod(np.take((16,8,4), 0))` = `16`
  - Multi: `np.prod(np.take((16,8,4), (0,1,2)))` = `512`
- The rest of the logic (mask.sum, null_mask calculation) already works for tuple axes

## Edit Sites

**File**: `xarray/core/nanops.py`

1. **Lines 28-31**: Remove the ValueError check entirely
   - Current: Raises error when axis has `__len__`
   - Change: Delete these 4 lines

2. **Line 35**: Replace scalar indexing with tuple-compatible calculation
   - Current: `null_mask = (mask.shape[axis] - mask.sum(axis) - min_count) < 0`
   - Change: `null_mask = (np.prod(np.take(mask.shape, axis)) - mask.sum(axis) - min_count) < 0`

## Affected Functions
- `nansum` (line 115): calls `_maybe_null_out` with min_count
- `nanprod` (line 185): calls `_maybe_null_out` with min_count

Both will gain multi-dimensional min_count support after the fix.

## Gate Loop - Iteration 1

**Hypothesis**: Remove ValueError guard blocking multi-dimensional reduction and replace `mask.shape[axis]` with `np.prod(np.take(mask.shape, axis))` to handle tuple axes.

**Implementation**:
- Removed lines 28-31: ValueError check that raised "min_count is not available for reduction with more than one dimensions"
- Replaced line 35: Changed `mask.shape[axis]` to conditional logic:
  - If axis is tuple/list: `axis_size = np.prod(np.take(mask.shape, axis))`
  - Otherwise: `axis_size = mask.shape[axis]`

**Codex review**: Approved with suggestion to expand one-liner into if-else for better formatting.

**Gate result**: ✓ GREEN - All 612 tests passed, including all FAIL_TO_PASS tests:
- test_min_count_nd[sum-False-{float,int,float32,bool_}] ✓
- test_min_count_nd[prod-False-{float,int,float32,bool_}] ✓
- No PASS_TO_PASS regressions

**Trajectory**: Convergent-resolved (first iteration success)

**Resolution**: The recon diagnosis was correct. Multi-dimensional reduction with min_count now works by computing the total size of reduced dimensions using `np.prod(np.take(mask.shape, axis))` instead of the single-dimension `mask.shape[axis]`.

---

# Audit: pydata__xarray-4356

## FAIL_TO_PASS
- `xarray/tests/test_duck_array_ops.py::test_min_count_nd[sum-False-float]`: PASS ✓
- `xarray/tests/test_duck_array_ops.py::test_min_count_nd[sum-False-int]`: PASS ✓
- `xarray/tests/test_duck_array_ops.py::test_min_count_nd[sum-False-float32]`: PASS ✓
- `xarray/tests/test_duck_array_ops.py::test_min_count_nd[sum-False-bool_]`: PASS ✓
- `xarray/tests/test_duck_array_ops.py::test_min_count_nd[prod-False-float]`: PASS ✓
- `xarray/tests/test_duck_array_ops.py::test_min_count_nd[prod-False-int]`: PASS ✓
- `xarray/tests/test_duck_array_ops.py::test_min_count_nd[prod-False-float32]`: PASS ✓
- `xarray/tests/test_duck_array_ops.py::test_min_count_nd[prod-False-bool_]`: PASS ✓

## PASS_TO_PASS regressions
None. Gate shows 612 passed, 0 failed. Spot-checked:
- `TestOps::test_first`: PASS ✓
- `TestOps::test_last`: PASS ✓
- `TestOps::test_count`: PASS ✓

## Pre-existing failures (not counted, confirmed against base capture)
None

## Patch
```diff
diff --git a/xarray/core/nanops.py b/xarray/core/nanops.py
index 41c8d258..e327fbdf 100644
--- a/xarray/core/nanops.py
+++ b/xarray/core/nanops.py
@@ -26,13 +26,12 @@ def _maybe_null_out(result, axis, mask, min_count=1):
     """
     xarray version of pandas.core.nanops._maybe_null_out
     """
-    if hasattr(axis, "__len__"):  # if tuple or list
-        raise ValueError(
-            "min_count is not available for reduction with more than one dimensions."
-        )
-
     if axis is not None and getattr(result, "ndim", False):
-        null_mask = (mask.shape[axis] - mask.sum(axis) - min_count) < 0
+        if hasattr(axis, "__len__"):
+            axis_size = np.prod(np.take(mask.shape, axis))
+        else:
+            axis_size = mask.shape[axis]
+        null_mask = (axis_size - mask.sum(axis) - min_count) < 0
         if null_mask.any():
             dtype, fill_value = dtypes.maybe_promote(result.dtype)
             result = result.astype(dtype)
```

## Summary
The fix successfully enables multi-dimensional reduction with `min_count` by:
1. Removing the ValueError that blocked tuple/list axes
2. Computing total axis size via `np.prod(np.take(mask.shape, axis))` for multi-axis cases
3. Preserving existing behavior for single-axis reductions

All 8 FAIL_TO_PASS tests now pass. No regressions detected across 612 tests.

VERDICT: RESOLVED
RE-ENTER: none
