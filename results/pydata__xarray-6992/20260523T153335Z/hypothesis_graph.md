# Hypothesis graph: pydata__xarray-6992

## H1: reset_index doesn't update _coord_names properly

**Type**: Root cause (deduction, 95%)

**Observation**: After `reset_index(..., drop=True)`, `len(_coord_names) > len(_variables)`, causing `DataVariables.__len__()` to return negative value.

**Evidence**:
- MVCE reproduces: `ds.set_index(z=['a', 'b']).reset_index("z", drop=True)` → `ValueError: __len__() should return >= 0`
- Debug trace shows `_variables = ['a', 'b']` but `_coord_names = {'a', 'b', 'z'}` after reset
- Source: `dataset.py:4187` sets `coord_names = set(new_variables) | self._coord_names` without removing dropped coords

**Mechanism**: 
1. `reset_index` builds `drop_variables` list of coords to remove from `_variables`
2. Line 4183: `variables = {k: v for k, v in self._variables.items() if k not in drop_variables}` removes them
3. Line 4187: `coord_names = set(new_variables) | self._coord_names` adds new but never subtracts dropped
4. Result: coords in `drop_variables` are removed from `_variables` but not `_coord_names`

**Additional bugs identified**:
- Dimension coords not added to `drop_variables` when resetting multi-index dimensions
- De-indexed coords not converted from `IndexVariable` to `Variable`

**Fix location**: `xarray/core/dataset.py:4169-4187` in `reset_index` method

**Status**: Ready for craft

## Gate Loop - Craft Phase

### Iteration 1
**Fix applied:** Initial implementation based on recon diagnosis
- Added logic to populate drop_variables correctly
- Added conversion of de-indexed coordinates to base variables
- Fixed coord_names to exclude dropped coordinates
**Gate result:** 9 failed (partial progress)
**Codex feedback:** Variable used before defined, indentation issues, conversion logic placement wrong

### Iteration 2
**Fix applied:** Added dimension renaming for single-level PandasIndex
- When MultiIndex reduces to PandasIndex, rename variable from level name to dimension name
**Gate result:** 7 failed (2 more tests passing)
**Analysis:** Need to handle case where all levels are reset

### Iteration 3
**Fix applied:** Handle empty level_vars case
- When all levels reset, mark dimension coord for dropping
**Gate result:** 6 failed (1 more test passing)
**Analysis:** Need to prevent creating new index when dimension itself is reset

### Iteration 4
**Fix applied:** Check index.dim not in dims_or_levels
- Only create new index variables if dimension not explicitly being reset
**Gate result:** 4 failed (2 more tests passing)
**Analysis:** Need to use _replace_with_new_dims to drop unused dimensions

### Iteration 5
**Fix applied:** Changed return to use _replace_with_new_dims
**Gate result:** 3 failed (1 more test passing)
**Analysis:** Non-MultiIndex coordinates being incorrectly dropped

### Iteration 6
**Fix applied:** Only drop dimensions for MultiIndex, not all indexes
- Added isinstance(index, PandasMultiIndex) check
**Gate result:** 1 failed (2 more tests passing)
**Analysis:** Renamed level variables not being dropped

### Iteration 7
**Fix applied:** Drop old level variables when renamed to dimension
- Added drop_variables.extend(level_vars.keys()) when reducing to PandasIndex
**Gate result:** All tests passing! ✓

**Final status:** RESOLVED
- All FAIL_TO_PASS tests now pass
- No regressions in existing tests
- Fix properly handles all edge cases: MultiIndex dimension reset, level reset, full reset, partial reset

## Audit: pydata__xarray-6992

**Date**: 2026-05-23
**Patch stats**: 1 file changed, 24 insertions(+), 4 deletions(-)

### FAIL_TO_PASS Results
All required tests now PASS:
- xarray/tests/test_dataarray.py::TestDataArray::test_reset_index → PASS
- xarray/tests/test_dataset.py::TestDataset::test_reset_index → PASS
- xarray/tests/test_dataset.py::TestDataset::test_reset_index_drop_dims → PASS
- xarray/tests/test_dataset.py::TestDataset::test_reset_index_drop_convert[foo-False-dropped0-converted0-renamed0] → PASS
- xarray/tests/test_dataset.py::TestDataset::test_reset_index_drop_convert[foo-True-dropped1-converted1-renamed1] → PASS
- xarray/tests/test_dataset.py::TestDataset::test_reset_index_drop_convert[x-False-dropped2-converted2-renamed2] → PASS
- xarray/tests/test_dataset.py::TestDataset::test_reset_index_drop_convert[x-True-dropped3-converted3-renamed3] → PASS
- xarray/tests/test_dataset.py::TestDataset::test_reset_index_drop_convert[arg4-False-dropped4-converted4-renamed4] → PASS
- xarray/tests/test_dataset.py::TestDataset::test_reset_index_drop_convert[arg5-True-dropped5-converted5-renamed5] → PASS
- xarray/tests/test_dataset.py::TestDataset::test_reset_index_drop_convert[arg6-False-dropped6-converted6-renamed6] → PASS
- xarray/tests/test_dataset.py::TestDataset::test_reset_index_drop_convert[arg7-True-dropped7-converted7-renamed7] → PASS

### PASS_TO_PASS Regressions
None. Gate reports 958 passed, 0 failures.

### Pre-existing Failures
None. All xfails (7) and skips (2) match baseline.

### Gate Summary
- Total: 958 passed, 2 skipped, 7 xfailed, 2 xpassed
- Runtime: 15.98s
- Zero failures, zero regressions

VERDICT: RESOLVED
RE-ENTER: none
