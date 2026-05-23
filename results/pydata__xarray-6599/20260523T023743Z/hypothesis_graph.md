# Hypothesis graph: pydata__xarray-6599

## Hypothesis Node: H0 - Initial Observation (2026-05-22)

**Status:** Confirmed root cause

**Failure mode:** `test_polyval[timedelta-False]` fails with `UFuncBinaryResolutionError` when trying to subtract datetime64 from timedelta64.

**Error trace:**
```
xarray/core/computation.py:1908 -> _ensure_numeric(coord)
xarray/core/computation.py:1949 -> to_floatable(data)
xarray/core/computation.py:1938 -> datetime_to_numeric(..., offset=np.datetime64("1970-01-01"), ...)
xarray/core/duck_array_ops.py:434 -> array - offset
numpy.core._exceptions._UFuncBinaryResolutionError: ufunc 'subtract' cannot use operands with types dtype('<m8[ns]') and dtype('<M8[D]')
```

**Root cause:**
The `_ensure_numeric` function in `xarray/core/computation.py` (lines 1920-1949) incorrectly uses a hardcoded `offset=np.datetime64("1970-01-01")` for ALL datetime-like types (both datetime64 'M' and timedelta64 'm').

At line 1936, the condition `if x.dtype.kind in "mM"` matches both:
- datetime64 arrays (kind='M') - where the 1970-01-01 offset is correct
- timedelta64 arrays (kind='m') - where the 1970-01-01 offset causes a type error

When `datetime_to_numeric` tries to compute `array - offset` at `duck_array_ops.py:434`, it fails because:
- `array` is timedelta64[ns] (relative time duration)
- `offset` is datetime64[D] (absolute time point)
- NumPy doesn't allow subtracting an absolute time from a relative duration

**Evidence:**
- `xarray/core/computation.py:1936-1942` - the buggy code treats 'm' and 'M' identically
- The bug was introduced in commit `6fbeb131` which rewrote polyval to use Horner's algorithm
- The old implementation used `get_clean_interp_index` which handled timedelta by casting directly to float64
- Timedelta64 can be directly cast to float without needing `datetime_to_numeric`

**Confidence:** Deduction - 98% (traced through code, error is deterministic)


---

## Gate Loop — Iteration 1

**Status**: RESOLVED ✅

**Applied fix**:
- Modified `xarray/core/computation.py:1936-1950`
- Split the condition `if x.dtype.kind in "mM"` into separate branches:
  - `if x.dtype.kind == "M"`: datetime64 → uses `datetime_to_numeric` with `offset=np.datetime64("1970-01-01")`
  - `elif x.dtype.kind == "m"`: timedelta64 → uses `datetime_to_numeric` with `offset=np.timedelta64(0, "ns")`

**codex volley 1** (draft review):
- REJECTED: Initial draft used `x.data.astype(float)` for timedelta
- Issues found:
  1. `astype(float)` is unit-dependent (doesn't normalize to nanoseconds)
  2. Mishandles NaT (converts to `-9.22337204e18` instead of `nan`)
  3. Bypasses xarray's datetime conversion helper

**codex volley 2** (revised review):
- APPROVED: Revised to use `datetime_to_numeric` with `offset=np.timedelta64(0, "ns")`
- Addresses all three concerns:
  - Unit normalization via `datetime_unit="ns"` parameter
  - NaT → nan conversion (confirmed via NumPy behavior checks)
  - Consistent with xarray's datetime handling patterns

**Gate result**: ✅ GREEN
- FAIL_TO_PASS test `test_polyval[timedelta-False]` now PASSES
- All 265 tests passed (1 skipped, unrelated)
- No regressions in datetime handling (`test_polyval[datetime-False]`, `test_polyval[datetime-True]` still pass)

**Trajectory**: Convergent (first attempt) — recon diagnosis was accurate, codex review prevented unit-dependency bug, gate validated fix.
# Audit: pydata__xarray-6599

## FAIL_TO_PASS
- test_polyval[timedelta-False]: **PASSED** ✓

## PASS_TO_PASS regressions
none

## Pre-existing (not counted, confirmed against base capture)
none

## Summary
The patch successfully resolved the issue. The target test `test_polyval[timedelta-False]` now passes, and no regressions were introduced. All 265 tests passed with 1 skipped (pre-existing).

The craft patch added timedelta type handling to `_ensure_numeric()` in `xarray/core/computation.py`, which allows polyval to accept timedelta coordinates without raising a TypeError.

VERDICT: RESOLVED
RE-ENTER: none

---

