# Hypothesis graph: astropy__astropy-13236

## H₀: Auto-transform blocks Column/MaskedColumn creation
**Type**: Abduction → Deduction
**Status**: Active
**Confidence**: 99%

### Observation
- test_ndarray_mixin[False]: Expects Column, gets NdarrayMixin
  - Error: assert isinstance(t['a'], Column) fails, t['a'] is NdarrayMixin
- test_structured_masked_column: Expects MaskedColumn, gets NdarrayMixin
  - Error: AttributeError: 'NdarrayMixin' object has no attribute 'mask'

### Localization
File: astropy/table/table.py
Function: _convert_data_to_col (line 1179)
Suspect lines: 1242-1247

### Root Cause
The auto-transform at lines 1242-1247 converts ALL structured ndarrays (including np.ma.MaskedArray) to NdarrayMixin before the code can check if they should be MaskedColumn (line 1286-1290).

Flow for masked structured array:
1. Line 1244: Check passes (np.ma.MaskedArray is an np.ndarray with structured dtype)
2. Line 1246: Data converted to NdarrayMixin, data_is_mixin = True
3. Line 1268: Early return because data_is_mixin is True
4. Line 1286: Masked array check never executes

Flow for regular structured array:
1. Line 1244: Check passes (structured np.ndarray)
2. Line 1246: Data converted to NdarrayMixin, data_is_mixin = True
3. Line 1268: Early return because data_is_mixin is True
4. Line 1313: Column creation never executes

### Supporting Evidence
- astropy/table/table.py:1242-1247: Auto-transform code
- astropy/table/table.py:1286-1290: Masked array handling (never reached)
- Verified: Column and MaskedColumn already support structured dtypes
- Only auto-transform location in codebase

### Fix
Remove lines 1242-1247. This allows:
- Regular structured arrays → fall through to col_cls = self.ColumnClass at line 1313
- Masked structured arrays → caught by check at line 1286, become MaskedColumn


## /craft gate loop - iteration 1

**Hypothesis tested**: Delete lines 1242-1247 in `astropy/table/table.py` (the auto-transform block for structured ndarrays to NdarrayMixin)

**Change applied**:
```diff
--- a/astropy/table/table.py
+++ b/astropy/table/table.py
@@ -1239,12 +1239,6 @@ class Table:
                                 f'{fully_qualified_name} '
                                 'did not return a valid mixin column')
 
-        # Structured ndarray gets viewed as a mixin unless already a valid
-        # mixin class
-        if (not isinstance(data, Column) and not data_is_mixin
-                and isinstance(data, np.ndarray) and len(data.dtype) > 1):
-            data = data.view(NdarrayMixin)
-            data_is_mixin = True
 
         # Get the final column name using precedence.  Some objects may not
         # have an info attribute. Also avoid creating info as a side effect.
```

**Codex review** (pre-gate): Confirmed fix is correct. Deletion allows structured arrays to fall through to proper Column/MaskedColumn handling.

**Gate result**:
- ✅ `astropy/table/tests/test_mixin.py::test_ndarray_mixin[False]` PASSED
- ✅ `astropy/table/tests/test_table.py::test_structured_masked_column` PASSED

**Other test results**:
- 2 pre-existing failures (verified to fail before fix):
  - `astropy/table/tests/test_mixin.py::test_skycoord_representation`
  - `astropy/table/tests/test_table.py::test_values_equal_part1`
- 646 other tests passed

**E-value classification**: Convergent success — both FAIL_TO_PASS tests pass on first iteration.

**Resolution**: RESOLVED — FAIL_TO_PASS tests pass, gate is green.

---

# Audit: astropy__astropy-13236

## FAIL_TO_PASS
- astropy/table/tests/test_mixin.py::test_ndarray_mixin[False]: **PASS** ✓
- astropy/table/tests/test_table.py::test_structured_masked_column: **PASS** ✓

## PASS_TO_PASS regressions
None.

## Pre-existing (not counted, confirmed against base capture)
- astropy/table/tests/test_mixin.py::test_skycoord_representation — TypeError in concatenate (failed on base)
- astropy/table/tests/test_table.py::test_values_equal_part1 — Failed to raise ValueError (failed on base)

## Gate summary
- 646 tests passed
- 2 tests failed (both pre-existing)
- 25 skipped
- 1 xfailed

## Verification
Cross-checked against `/tmp/swebench-abduction/r4_failbase_astropy__astropy-13236.txt`:
- Base had 4 failures: test_skycoord_representation, test_ndarray_mixin[False], test_values_equal_part1, test_structured_masked_column
- Patch fixed 2 of them (the FAIL_TO_PASS tests)
- The other 2 remain as pre-existing failures unrelated to this fix

VERDICT: RESOLVED
RE-ENTER: none
