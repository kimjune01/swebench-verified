# Hypothesis graph: pydata__xarray-3095

## H₁: IndexVariable.copy(deep=True) loses dtype when creating new PandasIndexAdapter

**Mode**: Deduction
**Confidence**: 95%
**Status**: Active

### Observation
Test `test_copy[str-True]` fails with:
```
AssertionError: assert dtype('<U32') == dtype('O')
```

Original IndexVariable has dtype='<U32', but after copy(deep=True), dtype becomes 'object'.

### Root Cause
At `xarray/core/variable.py:1950`, IndexVariable.copy() creates a new PandasIndexAdapter without preserving the original dtype:

```python
data = PandasIndexAdapter(self._data.array.copy(deep=True))
```

### Why This Happens
1. `self._data.array` is a pandas.Index
2. `copy(deep=True)` on a pandas.Index with unicode strings returns an Index with object dtype (pandas limitation)
3. PandasIndexAdapter.__init__() without dtype parameter infers dtype from the Index
4. Since the Index has object dtype, PandasIndexAdapter sets self._dtype = np.dtype('O')
5. Original unicode dtype is lost

### Evidence
- `xarray/core/variable.py:1950` - PandasIndexAdapter created without dtype parameter
- `xarray/core/indexing.py:1231-1242` - PandasIndexAdapter.__init__ infers dtype when not provided
- Verified with test: pandas.Index converts '<U3' arrays to object dtype

### Fix
Pass the original dtype when creating the new PandasIndexAdapter:
```python
data = PandasIndexAdapter(self._data.array.copy(deep=True), dtype=self._data.dtype)
```

### Edit Sites
- `xarray/core/variable.py` line 1950: Add `dtype=self._data.dtype` parameter to PandasIndexAdapter constructor


## Gate iteration 1 (craft)

**Applied fix:**
```python
# xarray/core/variable.py:1950
data = PandasIndexAdapter(self._data.array.copy(deep=True), dtype=self._data.dtype)
```

**Gate result:** ✅ PASSED
- `TestIndexVariable::test_copy[str-True]`: PASSED
- Total: 254 passed, 11 xfailed, 0 failed
- No PASS_TO_PASS regressions

**Verdict:** RESOLVED — FAIL_TO_PASS test passes, no regressions detected.


## Audit: pydata__xarray-3095

**Patch confirmed live:** 1 file changed (xarray/core/variable.py)

### Gate Results (254 passed, 11 xfailed, 0 failed)

**FAIL_TO_PASS (1/1):**
- `xarray/tests/test_variable.py::TestIndexVariable::test_copy[str-True]`: **PASSED** ✅

**PASS_TO_PASS regressions:**
- None. All 254 tests passed with no failures.

**Pre-existing (not counted):**
- 11 xfailed tests (expected failures, not regressions):
  - TestVariableWithDask::test_0d_object_array_with_list
  - TestVariableWithDask::test_array_interface
  - TestVariableWithDask::test_copy_index
  - TestVariableWithDask::test_eq_all_dtypes
  - TestIndexVariable::test_getitem_error
  - TestIndexVariable::test_getitem_advanced
  - TestIndexVariable::test_getitem_fancy
  - TestIndexVariable::test_getitem_uint
  - TestIndexVariable::test_pad
  - TestIndexVariable::test_rolling_window
  - TestIndexVariable::test_coarsen_2d

### Analysis
The patch correctly preserves dtype when copying IndexVariable with deep=True by passing `dtype=self._data.dtype` to the PandasIndexAdapter constructor. The FAIL_TO_PASS test now passes, confirming the fix addresses the unicode dtype loss issue. No regressions introduced — all previously passing tests remain passing.
