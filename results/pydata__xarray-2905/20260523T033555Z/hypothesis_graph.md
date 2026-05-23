# Hypothesis graph: pydata__xarray-2905

## Hypothesis Node 1 (Initial Diagnosis)
**Time**: 2026-05-22
**Status**: Active
**Mode**: Deduction
**Confidence**: 95%

### Failure Summary
Test `xarray/tests/test_variable.py::TestAsCompatibleData::test_unsupported_type` fails when creating a Variable with a custom object that has a `.values` attribute.

Error:
```
ValueError: dimensions () must have the same length as the number of data dimensions, ndim=1
```

Test code:
```python
class CustomWithValuesAttr:
    def __init__(self, array):
        self.values = array

array = CustomWithValuesAttr(np.arange(3))
orig = Variable(dims=(), data=array)
assert isinstance(orig._data.item(), CustomWithValuesAttr)
```

Expected: Create a 0-dimensional Variable containing the `CustomWithValuesAttr` object as a scalar.
Actual: The `.values` attribute (a 1D array with 3 elements) is extracted, creating a 1D array, causing dimension mismatch.

### Root Cause
File: `xarray/core/variable.py`
Line: 221

```python
# we don't want nested self-described arrays
data = getattr(data, "values", data)
```

This line unconditionally extracts the `.values` attribute from ANY object that has one, not just pandas/xarray objects. This was introduced in PR #1746 (commit 5e801894) to handle item assignment.

The docstring states: "If data is already a pandas or xarray object (other than an Index), just use the values." But the implementation uses `getattr(data, "values", data)` which is too broad.

### Supporting Evidence
1. Line 221 in `as_compatible_data()` extracts `.values` from all objects indiscriminately
2. The test creates `CustomWithValuesAttr(np.arange(3))` where `.values = np.arange(3)` (a 1D array)
3. When Variable is created with `dims=()`, it expects ndim=0 but gets ndim=1 after `.values` extraction
4. Earlier checks handle Variable (line 204), NON_NUMPY_SUPPORTED_ARRAY_TYPES (line 207), but not arbitrary objects with `.values`

### Edit Sites
**File**: `xarray/core/variable.py`
**Lines**: 220-221
**Change**: Replace unconditional `getattr(data, "values", data)` with explicit type checking for pandas Series/DataFrame (pd.core.generic.NDFrame) and xarray DataArray/Dataset (common.DataWithCoords).

Current code:
```python
    # we don't want nested self-described arrays
    data = getattr(data, "values", data)
```

Should become:
```python
    # we don't want nested self-described arrays
    # Only extract .values from pandas Series/DataFrame or xarray DataArray/Dataset
    if isinstance(data, (pd.core.generic.NDFrame, common.DataWithCoords)):
        data = data.values
```

This ensures:
- pandas Series/DataFrame have `.values` extracted (pd.core.generic.NDFrame catches both)
- xarray DataArray/Dataset have `.values` extracted (common.DataWithCoords catches both)
- pandas Index does NOT have `.values` extracted (already handled in NON_NUMPY_SUPPORTED_ARRAY_TYPES)
- Variable does NOT have `.values` extracted (already handled earlier at line 204)
- Arbitrary objects with `.values` do NOT have `.values` extracted (this fixes the bug)

### Type Hierarchy Verification
- `pd.Series` and `pd.DataFrame` inherit from `pd.core.generic.NDFrame`
- `pd.Index` does NOT inherit from `pd.core.generic.NDFrame`
- `DataArray` and `Dataset` inherit from `common.DataWithCoords`
- `Variable` does NOT inherit from `common.DataWithCoords`

### Rejected Hypotheses
None - this is the first diagnosis.

### Open Questions
None - the root cause is clear from code inspection.

## Gate iteration 1 - SUCCESS

**Date:** 2026-05-22T20:15:00

**Change applied:**
Replaced unconditional `.values` extraction in `as_compatible_data()` at line 221 with type-checked version:

```python
# Old (line 221):
data = getattr(data, "values", data)

# New (lines 221-223):
# only extract .values from pandas Series/DataFrame or xarray DataArray/Dataset
if isinstance(data, (pd.core.generic.NDFrame, common.DataWithCoords)):
    data = data.values
```

**Gate result:** PASS
- FAIL_TO_PASS test `xarray/tests/test_variable.py::TestAsCompatibleData::test_unsupported_type` now passes
- All 365 tests passed (71 xfailed, 22 xpassed as expected)
- No regressions detected

**Analysis:**
The fix correctly restricts `.values` extraction to only pandas Series/DataFrame (subclasses of `pd.core.generic.NDFrame`) and xarray DataArray/Dataset (subclasses of `common.DataWithCoords`). Custom objects with `.values` attributes are no longer inadvertently unpacked, allowing them to be treated as opaque scalar objects as intended.

The test creates a `CustomWithValuesAttr` object with `.values = np.arange(3)` and stores it in a 0-dimensional Variable. Previously, `as_compatible_data()` would extract the 1D array from `.values`, causing a dimension mismatch. Now, the custom object passes through unchanged and is correctly wrapped as a scalar in a 0D array.

**Resolution:** RESOLVED ✓

## Audit: pydata__xarray-2905

**Date:** 2026-05-22
**Patch status:** Live (xarray/core/variable.py: 3 insertions, 1 deletion)

### FAIL_TO_PASS
- `xarray/tests/test_variable.py::TestAsCompatibleData::test_unsupported_type`: **PASSED** ✓

### PASS_TO_PASS regressions
None

### Pre-existing (not counted, confirmed against base capture)
- All 71 XFAIL tests match baseline (pandas/dask known issues)
- 22 XPASS tests (unexpected passes - improvements, not regressions)

### Verdict
All FAIL_TO_PASS tests pass. Zero regressions. The fix correctly restricts `.values` extraction to pandas Series/DataFrame and xarray DataArray/Dataset, allowing custom objects with `.values` attributes to be treated as opaque scalars as intended.

VERDICT: RESOLVED
RE-ENTER: none
