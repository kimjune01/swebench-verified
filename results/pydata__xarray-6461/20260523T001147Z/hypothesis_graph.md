# Hypothesis graph: pydata__xarray-6461

## Hypothesis H0 (abduction, 85%)
**Created:** 2026-05-22 - recon phase 1

**Symptom:** Test `test_where_attrs` fails with `IndexError: list index out of range` at `xarray/core/computation.py:1832`

**Root cause:** When `xr.where(cond, x, y, keep_attrs=True)` is called with scalar values for `x` and/or `y`, the lambda function at line 1832 tries to access `attrs[1]`, but scalars don't have attributes, so they don't appear in the attrs list passed to the lambda. When both `x` and `y` are scalars, the attrs list only contains one element (from `cond`), causing an IndexError.

**Code path:**
1. `xr.where(cond, 1, 0, keep_attrs=True)` is called
2. At line 1829-1832, `keep_attrs=True` is converted to `lambda attrs, context: attrs[1]`
3. `apply_ufunc` is called with cond, x=1, y=0
4. In `apply_variable_ufunc` (line ~763), it collects Variable objects: `objs = _all_of_type(args, Variable)`
5. Since x=1 and y=0 are scalars (not Variables), only `cond` is in `objs`
6. `attrs = [cond.attrs]` - a list with only one element
7. The lambda tries to access `attrs[1]`, which doesn't exist → IndexError

**Supporting evidence:**
- `xarray/core/computation.py:1832`: `keep_attrs = lambda attrs, context: attrs[1]`
- `xarray/core/computation.py:~763`: `attrs = merge_attrs([obj.attrs for obj in objs], combine_attrs=keep_attrs)`
- The attrs list only includes Variables, not scalars

**Secondary bug discovered:** When x is scalar and y is a DataArray, the current code returns y's attrs instead of empty attrs (because attrs[1] would be y.attrs, not x.attrs). The intended behavior is to keep attrs from x, so if x doesn't have attrs, the result should have empty attrs.

**Fix:** Replace the lambda with one that extracts x's attrs directly, before calling apply_ufunc:
```python
x_attrs = getattr(x, "attrs", {})
keep_attrs = lambda attrs, context: x_attrs
```

This works regardless of which arguments are scalars or DataArrays.


## Craft gate loop - iteration 1

**Hypothesis**: The `xr.where()` function with `keep_attrs=True` crashes when x and y are scalars because it tries to access `attrs[1]` when the attrs list only contains `[cond.attrs]`.

**Edit applied**: 
- File: `xarray/core/computation.py` lines 1832-1833
- Changed from: `keep_attrs = lambda attrs, context: attrs[1]`
- Changed to: 
  ```python
  x_attrs = getattr(x, "attrs", {})
  keep_attrs = lambda attrs, context: dict(x_attrs)
  ```

**Codex feedback**: Recommended returning `dict(x_attrs)` instead of `x_attrs` to avoid aliasing issues where mutating the result's attrs would mutate the input's attrs.

**Gate result**: ✅ PASSED
- All 248 tests passed, 1 skipped
- FAIL_TO_PASS test `xarray/tests/test_computation.py::test_where_attrs` now passes
- No regressions detected

**Trajectory**: Convergent (resolved in first iteration)

## Audit - iteration 1

**Patch verified live**: 
```
xarray/core/computation.py | 3 ++-
1 file changed, 2 insertions(+), 1 deletion(-)
```

**Change**: Lines 1832-1833 replaced `lambda attrs, context: attrs[1]` with early capture of `x.attrs` and `lambda attrs, context: dict(x_attrs)`

### FAIL_TO_PASS
- `xarray/tests/test_computation.py::test_where_attrs`: **PASSED** ✓

### PASS_TO_PASS regressions
none

### Pre-existing (not counted)
- 1 skipped test (dask/dask#7669) - confirmed in base capture, not related to this fix

### Gate summary
- 248 passed, 1 skipped
- Zero failures
- Zero regressions

