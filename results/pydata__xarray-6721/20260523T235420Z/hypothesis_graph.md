# Hypothesis graph: pydata__xarray-6721

---

## Node: Initial Diagnosis (2026-05-23)

**Hypothesis**: `get_chunksizes()` at `xarray/core/common.py:2026` triggers data loading by accessing `v.data` instead of `v._data` when checking for chunks attribute.

**Type**: Root cause diagnosis

**Reasoning mode**: Deduction

**Confidence**: 95%

**Evidence**:
1. Test `test_chunks_does_not_load_data` creates dataset with `InaccessibleVariableDataStore` that raises on data access
2. Stack trace: `Dataset.chunks` → `get_chunksizes()` → `hasattr(v.data, "chunks")` → `Variable.data` → `Variable.values` → `np.asarray()` → data load
3. `Variable.data` property (line 342) returns `self.values` when `self._data` is not a duck array
4. `LazilyIndexedArray` (zarr-backed data wrapper) lacks `__array_function__` and `__array_ufunc__`, so `is_duck_array()` returns False
5. Correct pattern already exists at `variable.py:1017`: `if hasattr(self._data, "chunks"):`

**Proposed fix**:
- `xarray/core/common.py:2026`: Change `if hasattr(v.data, "chunks"):` to `if hasattr(v._data, "chunks"):`

**Edit sites**:
- `xarray/core/common.py` line 2026

**Status**: Awaiting craft implementation and gate verification

---

## Node: Craft Implementation - Iteration 1 (2026-05-23)

**Action**: Applied the fix from recon diagnosis

**Edit**: Changed `xarray/core/common.py:2026` from `if hasattr(v.data, "chunks"):` to `if hasattr(v._data, "chunks"):`

**Volley**: codex review (pre-gate)
- Approved: "No functional issue with the one-line fix"
- Confirmed: Fix is consistent with existing pattern in `variable.py:1017`
- Note: Using private attribute `v._data` is acceptable for internal xarray code

**Gate result**: ✅ PASSED
- All 1406 tests passed
- Target test `test_chunks_does_not_load_data` now passes
- No regressions introduced

**Status**: RESOLVED — FAIL_TO_PASS tests pass

---

## Node: Audit Verification (2026-05-23)

**Phase 1: Patch confirmation**
- Patch live: `xarray/core/common.py` (1 insertion, 1 deletion)

**Phase 2: Gate execution**
- Full suite: 1406 passed, 33 skipped, 1 xfailed, 5 xpassed
- Runtime: 32.83s

**Phase 3: Classification**

### FAIL_TO_PASS
- `xarray/tests/test_dataset.py::TestDataset::test_chunks_does_not_load_data`: ✅ PASSED

### PASS_TO_PASS regressions
- None

### Pre-existing (not counted)
- None (all failures are expected: 1 xfailed per baseline)

### xpassed (not regressions, improvements)
- `TestDataset::test_copy_coords[False-expected_orig1]`
- `test_raise_no_warning_dask_rolling_assert_close[numpy-mean-2]`
- `test_raise_no_warning_dask_rolling_assert_close[numpy-max-2]`
- `test_raise_no_warning_dask_rolling_assert_close[dask-mean-2]`
- `test_raise_no_warning_dask_rolling_assert_close[dask-max-2]`

**Phase 4: Verdict**
- All FAIL_TO_PASS tests pass: ✅
- Zero PASS_TO_PASS regressions: ✅
- Contract fulfilled

VERDICT: RESOLVED
RE-ENTER: none
