# Hypothesis graph: pydata__xarray-6599

## Node: H₀ - Initial failure observation
**Type:** abduction  
**Status:** confirmed  
**Evidence:**
- Test: `test_polyval[timedelta-False]`
- Error: `numpy.core._exceptions._UFuncBinaryResolutionError: ufunc 'subtract' cannot use operands with types dtype('<m8[ns]') and dtype('<M8[D]')`
- Location: `/testbed/xarray/core/duck_array_ops.py:434` in `datetime_to_numeric`
- The error occurs when trying to subtract a datetime64 offset from a timedelta64 array

## Node: H₁ - Root cause identified
**Type:** deduction  
**Status:** active  
**Confidence:** 98%

The bug is in `_ensure_numeric` function's nested `to_floatable` helper (xarray/core/computation.py:1935-1944).

**Problem:** The function treats datetime64 (kind "M") and timedelta64 (kind "m") identically:
```python
def to_floatable(x: DataArray) -> DataArray:
    if x.dtype.kind in "mM":  # <-- treats both types the same
        return x.copy(
            data=datetime_to_numeric(
                x.data,
                offset=np.datetime64("1970-01-01"),  # <-- datetime offset for both
                datetime_unit="ns",
            ),
        )
    return x
```

**Why this fails:**
- For datetime64 arrays: subtracting a datetime offset produces a timedelta → correct
- For timedelta64 arrays: subtracting a datetime from a timedelta is a type error → wrong

**Evidence:**
1. xarray/core/computation.py:1936 checks `if x.dtype.kind in "mM"` - includes both datetime and timedelta
2. xarray/core/computation.py:1940 uses `offset=np.datetime64("1970-01-01")` for both
3. Stack trace shows `datetime_to_numeric` at line 434 tries `array - offset` → `timedelta64[ns] - datetime64[D]` → UFuncTypeError

**Historical context:**
- Introduced in commit 6fbeb131 "polyval: Use Horner's algorithm + support chunked inputs"
- Old implementation used `get_clean_interp_index` which handled timedelta64 by casting directly to float64
- New implementation incorrectly unified datetime64 and timedelta64 handling

**Verification:**
- `np.array([1000, 2000, 3000], dtype="timedelta64[ns]").astype(float)` → `[1000., 2000., 3000.]` ✓
- Expected test output: `[1000.0, 2000.0, 3000.0]`

## Edit sites
**File:** xarray/core/computation.py  
**Lines:** 1935-1944 (function `to_floatable` inside `_ensure_numeric`)

**Required change:** Split the datetime64 and timedelta64 handling:
1. For datetime64 (kind "M"): use `datetime_to_numeric` with datetime offset (current behavior)
2. For timedelta64 (kind "m"): convert directly to float without using `datetime_to_numeric`


## Craft iteration 1 (RESOLVED)

**Hypothesis**: Split timedelta64 and datetime64 handling in `_ensure_numeric.to_floatable` - use `datetime_to_numeric` with `offset=np.timedelta64(0, "ns")` for timedelta64, keep existing datetime offset for datetime64.

**Draft approach**: Initially tried simple `astype(float64)` for timedelta64, but codex caught that this doesn't normalize units (timedelta64[us] would return microseconds not nanoseconds) and converts NaT to a huge negative number instead of nan.

**Codex review**: Suggested using `datetime_to_numeric` with `offset=np.timedelta64(0, "ns")` for timedelta64 to maintain unit normalization and proper NaT handling.

**Implementation**: Modified `xarray/core/computation.py` lines 1935-1944:
- Split `if x.dtype.kind in "mM":` into two branches
- For kind "m" (timedelta64): use `datetime_to_numeric` with `offset=np.timedelta64(0, "ns")`
- For kind "M" (datetime64): keep existing `offset=np.datetime64("1970-01-01")`

**Gate result**: ✅ PASSED - All 265 tests passed including `test_polyval[timedelta-False]`

**E-value**: Convergent-resolved

**Resolution**: The fix correctly handles timedelta64 arrays by using a timedelta offset instead of a datetime offset, avoiding the type error while maintaining proper unit normalization to nanoseconds and NaT handling.
