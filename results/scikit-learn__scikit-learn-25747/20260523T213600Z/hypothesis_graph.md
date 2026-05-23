# Hypothesis graph: scikit-learn__scikit-learn-25747

## H₀: Initial Hypothesis (abduction)

**Status**: Active  
**Confidence**: 95% (deduction - traced code path, read implementation)  
**Mode**: Deduction

The test `test_set_output_pandas_keep_index` fails because `_wrap_in_pandas_container` unconditionally overwrites the index of DataFrames returned by transformers with the original input's index.

**Evidence**:
1. Test failure shows transformer returns DataFrame with index `["s0", "s1"]` but result has index `[0, 1]` (original input's index)
2. `sklearn/utils/_set_output.py:58-59`: When `data_to_wrap` is a DataFrame, code does `if index is not None: data_to_wrap.index = index`
3. `sklearn/utils/_set_output.py:132`: The `index` parameter is always `getattr(original_input, "index", None)`, which for DataFrame inputs will be the original index
4. Call path: `transform()` → `_wrap_method_output()` → `_wrap_data_with_container()` → `_wrap_in_pandas_container()`

**Root cause**:
Lines 58-59 in `sklearn/utils/_set_output.py` unconditionally override the index when `data_to_wrap` is a DataFrame, even when the transformer intentionally set a custom index (e.g., when aggregating data).

**Edit sites**:
- `sklearn/utils/_set_output.py` lines 58-59: Remove the index assignment when `data_to_wrap` is already a DataFrame. The transformer's index should be preserved.


---

## Craft Gate Loop

### Iteration 1: Initial fix

**Changes applied:**
- Removed lines 58-59 in `sklearn/utils/_set_output.py` that unconditionally overwrite DataFrame index
- Updated docstring to reflect that only `columns` are changed for DataFrames, not `index`

**Diff:**
```diff
--- a/sklearn/utils/_set_output.py
+++ b/sklearn/utils/_set_output.py
@@ -14,7 +14,7 @@ def _wrap_in_pandas_container(
 ):
     """Create a Pandas DataFrame.
 
-    If `data_to_wrap` is a DataFrame, then the `columns` and `index` will be changed
+    If `data_to_wrap` is a DataFrame, then the `columns` will be changed
     inplace. If `data_to_wrap` is a ndarray, then a new DataFrame is created with
     `columns` and `index`.
 
@@ -53,8 +53,6 @@ def _wrap_in_pandas_container(
     if isinstance(data_to_wrap, pd.DataFrame):
         if columns is not None:
             data_to_wrap.columns = columns
-        if index is not None:
-            data_to_wrap.index = index
         return data_to_wrap
 
     return pd.DataFrame(data_to_wrap, index=index, columns=columns)
```

**Codex review (pre-gate):**
- Noted docstring needs updating (applied)
- Confirmed patch is directionally correct for the bug
- No obvious breaks for ndarray-producing transformers

**Gate result:** ✅ **PASSED**
- All 15 tests passed, including `test_set_output_pandas_keep_index`
- FAIL_TO_PASS test now passes: transformer's custom DataFrame index `["s0", "s1"]` is preserved

**Resolution:** RESOLVED on iteration 1. The fix correctly preserves DataFrame indices set by transformers while still applying the original index when creating DataFrames from ndarrays.

---

## Audit: scikit-learn__scikit-learn-25747

**Patch verified live:**
```
 sklearn/utils/_set_output.py | 4 +---
 1 file changed, 1 insertion(+), 3 deletions(-)
```

**Full gate run:** All 15 tests passed (0.14s)

### FAIL_TO_PASS
- `sklearn/utils/tests/test_set_output.py::test_set_output_pandas_keep_index`: **PASS** ✓

### PASS_TO_PASS regressions
None — all 14 PASS_TO_PASS tests continue to pass.

### Pre-existing failures (not counted, confirmed against base capture)
None — the base capture showed only `test_set_output_pandas_keep_index` failing, which now passes.

### Classification summary
- **Baseline (fail-on-base):** 14 passed, 1 failed (`test_set_output_pandas_keep_index`)
- **With patch:** 15 passed, 0 failed
- **FAIL_TO_PASS contract:** 1/1 tests now pass ✓
- **PASS_TO_PASS contract:** 14/14 tests still pass ✓

**Patch correctness:** The fix removed lines 58-59 that unconditionally overwrote DataFrame indices. When `data_to_wrap` is already a DataFrame, the transformer's custom index is now preserved. When `data_to_wrap` is an ndarray, the index is still applied correctly during DataFrame construction.
