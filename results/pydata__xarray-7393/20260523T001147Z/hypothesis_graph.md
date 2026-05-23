# Hypothesis graph: pydata__xarray-7393

## H0: Initial observation (abduction)
The tests fail because after stacking a coordinate into a MultiIndex, the dtype changes from int32→int64 and float32→float64.

**Test failure:**
- `test_restore_dtype_on_multiindexes[int32]`: expects int32, gets int64
- `test_restore_dtype_on_multiindexes[float32]`: expects float32, gets float64

**Evidence:**
- Test creates Dataset with dtype int32/float32 coordinate
- Calls `.stack(baz=("bar",))` to create MultiIndex
- Resulting coordinate has dtype int64/float64 instead

## H1: Root cause - PandasMultiIndexingAdapter.__array__ ignores stored dtype (deduction - 95%)

**Diagnosis:**
The `PandasMultiIndexingAdapter` class stores the correct dtype in `self._dtype` but its `__array__` method (line 1536-1540 in xarray/core/indexing.py) doesn't apply it when extracting level values from the MultiIndex.

**Code path:**
1. `Dataset.stack()` → `_stack_once()` (dataset.py:4495)
2. `_stack_once()` creates MultiIndex via `index_cls.stack(product_vars, new_dim)` (dataset.py:4541)
3. `PandasMultiIndex.stack()` captures original dtypes in `level_coords_dtype` (indexes.py:714)
4. `PandasMultiIndex.create_variables()` creates `PandasMultiIndexingAdapter` with correct dtype (indexes.py:835)
5. When values are accessed, `PandasMultiIndexingAdapter.__array__()` is called (indexing.py:1536)
6. **BUG**: Line 1537 returns `self.array.get_level_values(self.level).values` directly without applying `self._dtype`

**Supporting evidence:**
```python
# xarray/core/indexing.py:1536-1540
def __array__(self, dtype: DTypeLike = None) -> np.ndarray:
    if self.level is not None:
        return self.array.get_level_values(self.level).values  # <- NO dtype conversion!
    else:
        return super().__array__(dtype)
```

Parent class correctly applies dtype (line 1436-1446):
```python
def __array__(self, dtype: DTypeLike = None) -> np.ndarray:
    if dtype is None:
        dtype = self.dtype  # <- uses stored dtype
    ...
    return np.asarray(array.values, dtype=dtype)  # <- applies dtype
```

**Experimental confirmation:**
```
data._dtype: int32  # <- correctly stored
get_level_values.values.dtype: int64  # <- pandas returns int64
np.asarray(data).dtype: int64  # <- __array__ doesn't convert
```

Pandas MultiIndex internally stores levels as int64/float64, but xarray captures the original dtype in `level_coords_dtype`. The adapter receives this dtype but fails to apply it.

**Edit site:**
- `xarray/core/indexing.py` lines 1536-1540: Make `PandasMultiIndexingAdapter.__array__` apply `self.dtype` to the result, matching parent class behavior

Confidence: **deduction - 95%** (traced code execution, confirmed with experiments)


## Craft Gate Loop

### Iteration 1: Initial Fix Applied

**Diff:**
```python
def __array__(self, dtype: DTypeLike = None) -> np.ndarray:
    if self.level is not None:
-       return self.array.get_level_values(self.level).values
+       if dtype is None:
+           dtype = self.dtype
+       return np.asarray(self.array.get_level_values(self.level).values, dtype=dtype)
    else:
        return super().__array__(dtype)
```

**Gate Result:** ✅ PASS

All 73 tests passed, including both FAIL_TO_PASS tests:
- `test_restore_dtype_on_multiindexes[int32]` - PASSED
- `test_restore_dtype_on_multiindexes[float32]` - PASSED

**Trajectory:** Convergent (success) - tests now pass

**Resolution:** The fix correctly applies the stored dtype to MultiIndex level values when converting to numpy arrays, matching the parent class pattern. No regressions observed.

---

## Audit: pydata__xarray-7393

### Patch Verification
**Patch status:** Live in tree (1 file changed: xarray/core/indexing.py)

**Gate execution:** Full test suite run on patched code
- Total tests: 73
- Result: All passed

### FAIL_TO_PASS Results
✅ `test_restore_dtype_on_multiindexes[int32]` - **PASSED**
   - Baseline: FAILED (AssertionError: assert 'int64' == 'int32')
   - Patched: PASSED

✅ `test_restore_dtype_on_multiindexes[float32]` - **PASSED**
   - Baseline: FAILED (AssertionError: assert 'float64' == 'float32')
   - Patched: PASSED

### PASS_TO_PASS Regressions
**None** - All 71 PASS_TO_PASS tests remain passing after the patch.

### Pre-existing Failures
**None** - No pre-existing failures in the test suite for this module.

### Verdict Analysis
The patch successfully resolves the issue:
- ✅ Both FAIL_TO_PASS tests now pass
- ✅ Zero regressions in PASS_TO_PASS tests  
- ✅ No new failures introduced

The fix in `PandasMultiIndexingAdapter.__array__()` correctly preserves dtype by:
1. Using `self.dtype` when no explicit dtype parameter is passed
2. Applying the dtype via `np.asarray(..., dtype=dtype)` to the level values

This matches the parent class pattern and prevents pandas' implicit int32→int64 and float32→float64 upcasting.
