# Hypothesis graph: pydata__xarray-4687

## H₀: Missing keep_attrs parameter (abduction, 90%)

**Observation**: Test `test_where_attrs` fails with `TypeError: where() got an unexpected keyword argument 'keep_attrs'`

**Root cause**: The `xr.where()` function at `xarray/core/computation.py:1730` does not accept a `keep_attrs` parameter. The test expects `xr.where(cond, x, y, keep_attrs=True)` to preserve attributes from the `x` argument when `keep_attrs=True`.

**Evidence**:
- `xarray/core/computation.py:1730`: Function signature is `def where(cond, x, y):` with no `keep_attrs` parameter
- `xarray/core/computation.py:1810-1817`: Current implementation calls `apply_ufunc` without passing `keep_attrs`
- `xarray/tests/test_computation.py:1929`: Test expects `attrs={"attr": "x"}` (from second argument `x`), not from `cond` or dropped

**Required changes**:
1. Add `keep_attrs` parameter to `where()` function signature (default `None`)
2. When `keep_attrs=True`, need custom handling because `apply_ufunc` with `keep_attrs="override"` would take attrs from first arg (`cond`), but test expects attrs from second arg (`x`)
3. Solution: Use a callable for `keep_attrs` that selects attrs from index 1 (x) instead of index 0 (cond)
4. Pass the processed `keep_attrs` to `apply_ufunc`

**Confidence**: Abduction — 90% (clear from error message and test expectation; implementation approach confirmed by reading `merge_attrs` and `apply_ufunc` code)


## Gate Loop - Iteration 1

**Action**: Applied fix with codex feedback incorporated:
- Added `keep_attrs=None` parameter to `where()` signature
- Resolved `keep_attrs=None` using `_get_keep_attrs(default=False)` to handle global options
- Used captured `x_attrs = getattr(x, "attrs", {})` instead of indexing callback args (avoiding indexing bugs when `cond` is scalar)
- Passed `keep_attrs` parameter to `apply_ufunc()`

**Result**: ✅ PASS

**Test output**:
- FAIL_TO_PASS test `xarray/tests/test_computation.py::test_where_attrs` PASSED
- All 248 tests in test_computation.py PASSED
- 1 pre-existing failure in test_units.py (unrelated to our change, verified by reverting)

**Status**: RESOLVED - All FAIL_TO_PASS tests pass.

---

# Audit: pydata__xarray-4687

## Phase 1: Patch confirmation
```
git diff --stat
 xarray/core/computation.py | 19 ++++++++++++++++++-
 1 file changed, 18 insertions(+), 1 deletion(-)
```
✅ Patch is live.

## Phase 2: Gate execution
Full gate executed: `pytest -rA xarray/tests/test_computation.py xarray/tests/test_units.py`

Results: 1 failed, 1760 passed, 693 skipped, 112 xfailed, 12 xpassed

## Phase 3: Classification

### FAIL_TO_PASS
- `xarray/tests/test_computation.py::test_where_attrs`: **PASS** ✅

### PASS_TO_PASS (all from test_computation.py)
All 248 tests in test_computation.py passed, including:
- test_signature_properties: PASS
- test_result_name: PASS
- test_ordered_set_union: PASS
- test_ordered_set_intersection: PASS
- test_join_dict_keys: PASS
- test_collect_dict_values: PASS
- test_apply_identity: PASS
- test_apply_two_inputs: PASS
- test_apply_1d_and_0d: PASS
- test_apply_two_outputs: PASS
- test_apply_dask_parallelized_two_outputs: PASS
- test_apply_input_core_dimension: PASS
- test_apply_output_core_dimension: PASS
- (and all 235+ other tests from the PASS_TO_PASS list)

**Result**: All PASS_TO_PASS tests passed ✅

### PASS_TO_PASS regressions
**None**

### Pre-existing failures (not counted)
- `xarray/tests/test_units.py::TestPintWrappingDask::test_duck_array_ops`
  - Error: `AssertionError: assert <class 'pint.registry.Quantity'> == <class 'pint.Quantity'>`
  - **Reason for exclusion**: This test is NOT in the FAIL_TO_PASS or PASS_TO_PASS lists. The failure is a Pint type comparison issue in a test that uses `mean()`, completely unrelated to the `where()` function modified by this patch. The hypothesis graph from craft phase (line 36) already documented this as "pre-existing failure in test_units.py (unrelated to our change, verified by reverting)".

## Phase 4: Verdict

**Contract fulfilled**:
- ✅ All FAIL_TO_PASS tests pass (1/1)
- ✅ Zero PASS_TO_PASS regressions (0 regressions)

VERDICT: RESOLVED
RE-ENTER: none
