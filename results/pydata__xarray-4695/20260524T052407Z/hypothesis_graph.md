# Hypothesis graph: pydata__xarray-4695

## H₀: Dimension name collision with sel() parameters (abduction, 95%)

**Observation**: Test `test_loc_dim_name_collision_with_sel_params` fails with `TypeError: ``method`` must be a string` when accessing a DataArray via `.loc` with a dimension named "method".

**Stack trace analysis**:
- `_LocIndexer.__getitem__` (dataarray.py:199) calls `self.data_array.sel(**key)`
- When `key = {'dim1': ['x', 'y'], 'method': ['a']}`, this unpacks to `sel(dim1=['x', 'y'], method=['a'])`
- The `sel()` method has a parameter named `method` (expected type: str for fill methods like 'ffill', 'bfill')
- The dimension indexer `method=['a']` collides with the parameter name, causing type error

**Root cause**: `xarray/core/dataarray.py:199` unpacks the indexer dict as keyword arguments, causing dimension names to collide with reserved parameter names (`method`, `tolerance`, `drop`).

**Supporting evidence**:
- Dataset's `_LocIndexer` (dataset.py:504) correctly uses `self.dataset.sel(key)` without unpacking
- Both `DataArray.sel()` and `Dataset.sel()` accept indexers via the `indexers` parameter OR via `**indexers_kwargs`
- Unpacking forces dimension names into the keyword argument namespace, where they collide with parameter names

**Edit site**: `xarray/core/dataarray.py:199` - change `return self.data_array.sel(**key)` to `return self.data_array.sel(key)`

**Confidence**: 95% deduction - traced the exact code path and identified the parameter collision

## Craft gate-loop iteration 1

**Applied fix**: Changed `xarray/core/dataarray.py:199` from `return self.data_array.sel(**key)` to `return self.data_array.sel(key)`

**Rationale**: The `**key` unpacking caused dimension names to collide with `sel()` method parameters (method, tolerance, drop). Passing the dict directly as the `indexers` parameter avoids the collision, matching the pattern used in Dataset's `_LocIndexer`.

**codex pre-gate review**: Directionally correct, no obvious behavioral regression. Confirmed that `DataArray.sel()` accepts `indexers` as first positional parameter.

**Gate result**: ✓ **PASS**
- Target test `test_loc_dim_name_collision_with_sel_params`: **PASSED**
- All 6 `.loc` related tests: **PASSED** (test_loc, test_loc_datetime64_value, test_loc_assign, test_loc_assign_dataarray, test_loc_single_boolean, test_loc_dim_name_collision_with_sel_params)
- One unrelated test failure (`test_from_series_multiindex`) due to pandas/xarray version incompatibility, not related to this change

**Trajectory**: Convergent-resolved in 1 iteration

**Resolution**: The fix correctly resolves the dimension name collision issue by passing the indexer dict directly to `sel()` instead of unpacking it as keyword arguments.

## Audit: pydata__xarray-4695

### FAIL_TO_PASS
- test_loc_dim_name_collision_with_sel_params: **PASSED** ✓

### PASS_TO_PASS regressions
None - all 12 PASS_TO_PASS tests verified passing:
- test_repr: PASSED
- test_repr_multiindex: PASSED
- test_repr_multiindex_long: PASSED
- test_properties: PASSED
- test_data_property: PASSED
- test_indexes: PASSED
- test_get_index: PASSED
- test_get_index_size_zero: PASSED
- test_struct_array_dims: PASSED
- test_name: PASSED
- test_dims: PASSED
- test_sizes: PASSED

### Pre-existing (not counted, confirmed against base capture)
- test_from_series_multiindex: ImportError from Pandas version check rejecting xarray dev version (0.16.3.dev23). This is an environmental issue unrelated to the `_LocIndexer` fix - the error occurs during `pandas.DataFrame.to_xarray()` before any affected code paths execute.

### Full contract satisfied
✓ All FAIL_TO_PASS tests pass
✓ Zero PASS_TO_PASS regressions
✓ Fix resolves dimension name collision by passing indexer dict directly to sel() instead of unpacking

