# Hypothesis graph: pydata__xarray-7229

## H0: Baseline Observation (Abduction)
The test `test_where_attrs` fails because coordinate attributes are being overwritten with the main DataArray attributes. Specifically, when calling `xr.where(cond, x, y, keep_attrs=True)`, the coordinate `x["a"].attrs` should be `{"attr": "x_coord"}` but instead gets `{"attr": "x_da"}` (the main variable's attributes).

**Confidence: Abduction — 85%**

## H1: Root Cause - Lambda in `where()` ignores coordinate-specific attributes (Deduction)

**Location:** `xarray/core/computation.py:1863`

**Evidence:**
```python
if keep_attrs is True:
    # keep the attributes of x, the second parameter, by default to
    # be consistent with the `where` method of `DataArray` and `Dataset`
    keep_attrs = lambda attrs, context: getattr(x, "attrs", {})
```

**Problem:** The lambda `lambda attrs, context: getattr(x, "attrs", {})` always returns the top-level DataArray attributes (`x.attrs`), even when merging coordinate attributes. 

**Call Flow:**
1. `xr.where(cond, x, y, keep_attrs=True)` creates lambda: `lambda attrs, context: getattr(x, "attrs", {})`
2. `apply_dataarray_vfunc()` calls `build_output_coords_and_indexes()` to merge coordinates
3. `merge_coordinates_without_align()` → `merge_collected()` → `merge_attrs()` is called for each coordinate
4. For coordinate 'a': `merge_attrs([cond['a'].attrs, x['a'].attrs, y['a'].attrs], combine_attrs=keep_attrs)`
5. The callable lambda ignores the `attrs` parameter and returns `x.attrs` instead of `attrs[1]` (which would be `x['a'].attrs`)

**Why PR #6461 changed from `attrs[1]`:** 
- Old code: `lambda attrs, context: attrs[1]`
- Problem: When `x` or `y` are scalars (e.g., `xr.where(cond, 1, 0, keep_attrs=True)`), they don't have attrs
- In that case, `attrs = [cond.attrs]` (length 1), so `attrs[1]` raises IndexError
- PR #6461 fixed the scalar case but broke coordinate attributes

**Correct Solution:**
```python
keep_attrs = lambda attrs, context: attrs[1] if len(attrs) > 1 else {}
```

This:
- Returns `attrs[1]` (x's attributes or coordinate attributes) when both cond and x are DataArrays
- Returns `{}` when x is a scalar (attrs only has one element from cond)
- Preserves coordinate attributes correctly while handling the scalar case

**Confidence: Deduction — 98%**

## Gate Iteration 1: Positional indexing broken for mixed types

**Attempted fix:** `attrs[1] if len(attrs) > 1 else {}`

**Gate result:** FAIL - scalar-scalar and scalar-cond cases fail

**Evidence:** 
- When `cond=True` (scalar), `x` and `y` DataArrays: attrs = [x.attrs, y.attrs], so attrs[1] = y.attrs (WRONG)
- When both `x` and `y` are scalars: coordinate attrs from cond preserved (WRONG)

**Root cause:** Positional indexing is fundamentally broken because:
1. attrs list composition varies by context (Datasets get different lists than coordinates)
2. When cond is scalar, x shifts from index 1 to index 0
3. Coordinate attrs bypass the lambda when there's no merge (single source)

**New approach (from codex):** Disable attr merging (`keep_attrs=False`), then post-process by explicitly copying attrs from x.

**Confidence: Deduction — 95%**

## Gate Iteration 2-7: Incremental fixes for post-processing approach

**Implementation:** Set `preserve_attrs = keep_attrs is True`, then `keep_attrs = False`, then manually copy attrs from x after `apply_ufunc`.

**Progress:**
- Iteration 2-3: Added basic post-processing to copy x.attrs and coordinate attrs
- Iteration 4: Added else branch to clear all attrs when x is scalar
- Iteration 5: Fixed AttributeError by using isinstance check for Dataset
- Iteration 6-7: Handling mixed DataArray/Dataset cases

**Current state:** Most tests passing, failing on: `xr.where(cond, x.rename("x"), ds_y, keep_attrs=True)` where x is DataArray, result is Dataset

**Issue:** When x is DataArray but result is Dataset, need to copy x.attrs to result data variable, not just result.attrs.

**Confidence: In progress**

## Audit: pydata__xarray-7229

**Gate run:** 281 passed, 1 skipped, 0 failures

### FAIL_TO_PASS
- `xarray/tests/test_computation.py::test_where_attrs`: **PASSED** ✓

### PASS_TO_PASS regressions
None — all PASS_TO_PASS tests remain passing.

### Pre-existing (not counted, confirmed against base capture)
- 1 skipped test: `xarray/tests/test_computation.py:1309` (dask/dask#7669) — pre-existing skip, not a regression

### Analysis
The craft patch successfully resolves the issue. The FAIL_TO_PASS test now passes, and no regressions were introduced in the PASS_TO_PASS test suite. The gate output shows clean execution with 281 tests passing.

**Patch summary:** Modified `xarray/core/computation.py` to implement a post-processing approach for attribute preservation in `where()`, bypassing the broken lambda-based merge strategy.

VERDICT: RESOLVED
RE-ENTER: none
