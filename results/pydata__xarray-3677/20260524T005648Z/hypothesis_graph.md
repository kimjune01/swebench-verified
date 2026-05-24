# Hypothesis graph: pydata__xarray-3677

## H₀: DataArray not converted to Dataset in dataset_merge_method

**Type**: abduction  
**Confidence**: 95% (deduction)

The test fails because `Dataset.merge(dataarray)` does not convert the DataArray to a Dataset before processing, while the top-level `xr.merge([ds, da])` does.

### Evidence

1. **Stack trace** shows the failure at `xarray/core/merge.py:394` in `coerce_pandas_values`:
   ```python
   for k, v in obj.items():
   AttributeError: 'DataArray' object has no attribute 'items'
   ```

2. **Top-level merge** (line 790 in merge.py) explicitly handles DataArray:
   ```python
   obj = obj.to_dataset() if isinstance(obj, DataArray) else obj
   ```

3. **dataset_merge_method** (lines 797-837) accepts `other: "CoercibleMapping"` and passes it to `merge_core` without checking if it's a DataArray. At line 829, it tries to call `other.items()` which fails for DataArray.

4. **Dataset.merge docstring** (dataset.py:3558) says: `other : Dataset or castable to Dataset`, confirming DataArray should be supported.

### Root cause

`dataset_merge_method` does not convert DataArray to Dataset before processing it, but assumes `other` is dict-like (has `.items()` method). DataArray doesn't implement the dict-like interface.

### Edit sites

- `xarray/core/merge.py` lines 797-837: Add DataArray to Dataset conversion at the start of `dataset_merge_method`, after the imports, similar to what the top-level `merge()` function does at line 790.


## Craft: Gate Loop

### Iteration 1: Initial fix

**Drafted fix:**
```diff
--- a/xarray/core/merge.py
+++ b/xarray/core/merge.py
@@ -805,6 +805,10 @@ def dataset_merge_method(
 ) -> _MergeResult:
     """Guts of the Dataset.merge method.
     """
+    from .dataarray import DataArray
+
+    other = other.to_dataset() if isinstance(other, DataArray) else other
+
     # we are locked into supporting overwrite_vars for the Dataset.merge
     # method due for backwards compatibility
     # TODO: consider deprecating it?
```

**Codex volley:** "No blocking issue in the proposed runtime fix. Converting DataArray to Dataset before the overwrite_vars / merge_core path is the right place and should make ds.merge(da) match xr.merge([ds, da]). Verdict: patch is directionally correct; ship it with the regression test."

**Gate result:** ✅ PASS — All 22 tests passed, including `test_merge_dataarray`

**Trajectory:** Convergent success — the fix resolved the issue on the first attempt

**Resolution:** The minimal fix (4 lines: import DataArray + convert DataArray to Dataset) successfully makes `Dataset.merge(dataarray)` work by mirroring the pattern from the top-level `merge()` function. No regressions detected.

## Audit: pydata__xarray-3677

### Patch verification
✅ Patch is live: `xarray/core/merge.py` (+4 lines)

### FAIL_TO_PASS
- `xarray/tests/test_merge.py::TestMergeMethod::test_merge_dataarray`: **PASSED** ✓

### PASS_TO_PASS regressions
None — all 22 tests passed

### Pre-existing failures (not counted)
None

### Gate summary
- Collected: 22 items
- Passed: 22
- Failed: 0
- Warnings: 30 (deprecation warnings, not blocking)

All FAIL_TO_PASS tests now pass. Zero regressions introduced. The fix successfully converts DataArray to Dataset before processing in `dataset_merge_method`, matching the pattern from top-level `merge()`.

