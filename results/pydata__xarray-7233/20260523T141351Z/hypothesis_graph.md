# Hypothesis graph: pydata__xarray-7233

## H₀ (abduction, 85%)
**Node**: Initial observation  
**Claim**: The test fails because `Dataset.coarsen().construct()` demotes non-dimensional coordinates to data variables.  
**Evidence**: Test `test_coarsen_construct_keeps_all_coords` shows that coordinate 'day' exists in the input dataset but is missing from the output dataset's coordinates after calling `ds.coarsen(time=12).construct(time=("year", "month"))`. The assertion `assert list(da.coords) == list(result.coords)` fails with `['day'] == []`.

## H₁ (deduction, 95%)
**Node**: Root cause identified  
**Claim**: Line 976 in `xarray/core/rolling.py` only preserves coordinates that appear in the `window_dim` parameter, not all coordinates from the original object.  
**Evidence**:
- `xarray/core/rolling.py:976` — `should_be_coords = set(window_dim) & set(self.obj.coords)`
- When `window_dim = {'time': ('year', 'month')}` and `self.obj.coords = {'day'}`, the intersection is empty: `{'time'} & {'day'} = {}`
- This means no coordinates are preserved for datasets with non-dimensional coordinates
- In contrast, `DataArray.coarsen().construct()` works correctly because it uses `_from_temp_dataset()` which restores all coordinates

**Supporting code path**:
1. Input: Dataset with coordinate 'day' that depends on dimension 'time'
2. `Coarsen.construct()` processes all variables including 'day', reshaping it to ('year', 'month')
3. Line 976 computes `should_be_coords = set(window_dim) & set(self.obj.coords)` = `{}`
4. Line 977 calls `reshaped.set_coords(should_be_coords)` with empty set
5. Result: 'day' remains a data variable instead of being promoted to coordinate

## H₂ (rejected)
**Node**: Coordinates not being reshaped  
**Claim**: The 'day' coordinate is not being processed/reshaped during coarsening.  
**Killed by**: Verification shows 'day' IS present in the output, just as a data variable instead of a coordinate. The reshaping happens correctly; only the coordinate status is lost.

## Gate iteration 1 (craft)

**Hypothesis**: Line 976 in `xarray/core/rolling.py` uses set intersection that excludes non-dimensional coordinates not in `window_dim` keys.

**Edit**: Changed `should_be_coords = set(window_dim) & set(self.obj.coords)` to `should_be_coords = [name for name in self.obj.coords if name in reshaped.variables]`

**Codex review**: Suggested using list comprehension instead of set intersection to preserve coordinate ordering (test checks `list(result.coords)`).

**Gate result**: ✓ PASS — all 190 tests passed including `test_coarsen_construct_keeps_all_coords`

**Trajectory**: Convergent success (green gate on first attempt)

# Audit: pydata__xarray-7233

## Patch verification
```
xarray/core/rolling.py | 2 +-
1 file changed, 1 insertion(+), 1 deletion(-)
```

Changed line 976 from:
```python
should_be_coords = set(window_dim) & set(self.obj.coords)
```
to:
```python
should_be_coords = [name for name in self.obj.coords if name in reshaped.variables]
```

## FAIL_TO_PASS
- `xarray/tests/test_coarsen.py::TestCoarsenConstruct::test_coarsen_construct_keeps_all_coords`: **PASS** ✓

## PASS_TO_PASS regressions
None — all 190 tests passed, 8 skipped.

Verified sample from PASS_TO_PASS list:
- `test_coarsen_absent_dims_error[1-numpy]`: PASS ✓
- `test_coarsen_dataset[1-numpy-trim-left-True]`: PASS ✓
- All `test_coarsen_reduce` variants: PASS ✓
- All `test_coarsen_da_reduce` variants: PASS ✓
- `TestCoarsenConstruct::test_coarsen_construct[True]`: PASS ✓
- `TestCoarsenConstruct::test_coarsen_construct[False]`: PASS ✓

## Pre-existing failures
None confirmed — gate shows 0 failures.

## Kill report
Not applicable — fix is RESOLVED.

VERDICT: RESOLVED
RE-ENTER: none
