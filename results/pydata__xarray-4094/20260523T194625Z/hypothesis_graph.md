# Hypothesis graph: pydata__xarray-4094

---

## Hypothesis H0 — Initial Diagnosis
**Time:** 2026-05-23  
**Type:** deduction  
**Confidence:** 98%

### Symptom
The test `test_to_stacked_array_to_unstacked_dataset` fails with `MergeError: conflicting values for variable 'y' on objects to be combined` when attempting to roundtrip a Dataset with single-dimension variables through `to_stacked_array` → `to_unstacked_dataset`.

### Root Cause
In `to_unstacked_dataset` (xarray/core/dataarray.py:1964), when unstacking a DataArray with a single-level MultiIndex:
1. `self.sel({variable_dim: k})` selects a variable, reducing the MultiIndex to a scalar
2. `.squeeze(drop=True)` removes size-1 dimensions but does NOT drop scalar coordinates
3. Each variable retains the MultiIndex coordinate as a scalar with different values (e.g., 'y': ('a',) vs 'y': ('b',))
4. `Dataset(data_dict)` attempts to merge variables with conflicting scalar coordinate values → MergeError

This only occurs with single-level MultiIndexes; multi-level MultiIndexes unpack their remaining levels into regular coordinates, automatically removing the original MultiIndex coordinate.

### Evidence
- Stack trace: error at `xarray/core/merge.py:142` when merging variables
- Debug output: after `sel` + `squeeze`, single-level case has scalar 'y' coordinate, multi-level case does not
- Code inspection: `xarray/core/dataarray.py:1964` lacks coordinate cleanup after squeeze

### Proposed Fix
At `xarray/core/dataarray.py:1964`, after `squeeze(drop=True)`, conditionally drop the `dim` coordinate:
```python
data_array = self.sel({variable_dim: k}).squeeze(drop=True)
if dim in data_array.coords:
    data_array = data_array.reset_coords(dim, drop=True)
data_dict[k] = data_array
```

### Verification
Manual testing confirms this fix resolves the single-dimension case while preserving correctness for multi-dimension cases.

---

## Gate Loop Node — Craft Implementation
**Time:** 2026-05-23  
**Iteration:** 1  
**Status:** RESOLVED

### Drafted Fix
Based on recon diagnosis, implemented fix at `xarray/core/dataarray.py:1964`:
```python
# Old code:
data_dict[k] = self.sel({variable_dim: k}).squeeze(drop=True)

# New code:
data = self.sel({variable_dim: k}).squeeze(drop=True)
data_dict[k] = data.drop_vars(dim, errors="ignore")
```

### Codex Review
Codex suggested using `drop_vars(dim, errors="ignore")` instead of `reset_coords(dim, drop=True)` for:
- Better clarity of intent (explicitly dropping the variable)
- Error safety with `errors="ignore"` flag
- Less order-dependency concerns

### Gate Outcome
**PASS** - The FAIL_TO_PASS test `xarray/tests/test_dataset.py::TestDataset::test_to_stacked_array_to_unstacked_dataset` passes.

### Notes
- 4 categorical test failures observed in gate output are pre-existing environmental issues (pandas version check), verified unrelated to this change
- Fix uses `drop_vars` to remove the stacked coordinate that remains as a scalar after selection and squeeze
- Single iteration to resolution - recon diagnosis was accurate


---

## Audit Report — Regression Verification
**Time:** 2026-05-23  
**Instance:** pydata__xarray-4094

### Phase 1: Patch Verification
Patch is live in working tree:
```
 xarray/core/dataarray.py | 3 ++-
 1 file changed, 2 insertions(+), 1 deletion(-)
```

### Phase 2: Gate Execution
Full test suite run completed:
- 867 passed
- 4 failed
- 16 skipped
- 1 xfailed, 1 xpassed
- Total time: 8.93s

### Phase 3: Classification Against Baseline

#### FAIL_TO_PASS Status
- `xarray/tests/test_dataset.py::TestDataset::test_to_stacked_array_to_unstacked_dataset`: **PASSED** ✓

#### PASS_TO_PASS Regressions
**None**

#### Pre-existing Failures (not counted against fix)
All 4 failed tests are pre-existing environmental issues (pandas version check ImportError):
- `xarray/tests/test_dataset.py::TestDataset::test_sel_categorical`
- `xarray/tests/test_dataset.py::TestDataset::test_sel_categorical_error`
- `xarray/tests/test_dataset.py::TestDataset::test_categorical_multiindex`
- `xarray/tests/test_dataset.py::TestDataset::test_from_dataframe_categorical`

Error signature (all 4 tests):
```
ImportError: Pandas requires version '0.19.0' or newer of 'xarray' (version '0.15.2.dev110+ga64cf2d54' currently installed).
```

These failures are environment configuration issues unrelated to the patch (which only modifies dataarray.py:1964 for unstacking logic). The patch cannot cause pandas version check import errors.

### Phase 4: Verdict
All FAIL_TO_PASS tests pass. Zero PASS_TO_PASS regressions. The fix is complete and safe.

VERDICT: RESOLVED
RE-ENTER: none
