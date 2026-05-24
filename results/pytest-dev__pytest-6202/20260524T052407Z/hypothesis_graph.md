# Hypothesis graph: pytest-dev__pytest-6202

## Hypothesis Node: H1 - Naive string replacement in getmodpath()

**Status**: Active  
**Reasoning mode**: Deduction (traced code path, examined failing test output)  
**Confidence**: 95%

### Failure Summary
The failing test `test_example_items1` creates a parametrized test with parameter value `".[["`. The test expects:
- `items[3].name` to be `"testmethod_two[.[]"` ✓ (passes)
- `items[3].getmodpath()` to return `"TestY.testmethod_two[.[]"` ✗ (fails, returns `"TestY.testmethod_two[[]"`)

The actual error:
```
AssertionError: assert 'TestY.testmethod_two[[]' == 'TestY.testmethod_two[.[]'
  - TestY.testmethod_two[[]
  + TestY.testmethod_two[.[]
  ?                      +
```

### Root Cause
In `src/_pytest/python.py` line 289, the `getmodpath()` method ends with:
```python
s = ".".join(parts)
return s.replace(".[", "[")
```

The string replacement is too naive. It unconditionally replaces all occurrences of `".[["` with `"["`, which causes the following issue:

1. Parametrized test gets name `"testmethod_two[.[]"` (correct - created at line 416)
2. When building module path, parts are `["TestY", "testmethod_two[.[]"]`
3. After join: `"TestY.testmethod_two[.[]"`
4. After replace: `"TestY.testmethod_two[[]"` ← **BUG**: The ".[" inside the parameter value gets replaced

The replacement appears to be legacy code from 2008 (commit abc8cf09aa) that is no longer needed. Modern pytest includes the parameter part in the test item name itself, so there's no ".[" junction that needs to be collapsed.

### Supporting Evidence
- `src/_pytest/python.py:289` — `return s.replace(".[", "[")`
- `src/_pytest/python.py:416` — `subname = "{}[{}]".format(name, callspec.id)` — parameter already included in name
- `testing/test_collection.py:715` — Test assertion that fails due to this bug
- `git blame` shows the replace line dates to 2008, before current parametrization implementation

### Edit Sites
- `src/_pytest/python.py` line 289: Remove the `.replace(".[", "[")` call, change to `return s`

The fix is to change:
```python
return s.replace(".[", "[")
```
to:
```python
return s
```

### Verification
No other code in src/_pytest/ uses the pattern ".[" (verified via grep). Only one test currently fails (`test_example_items1`), which is the test added specifically for this bug fix (PR #6202).


## /craft gate loop

### Iteration 1: Initial fix applied

**Edit:** Removed `.replace(".[", "[")` from `getmodpath()` line 289 in `src/_pytest/python.py`

**Change:**
```python
# Before:
return s.replace(".[", "[")

# After:
return s
```

**Gate result:** ✅ PASS

All 73 tests passed, including the FAIL_TO_PASS test `testing/test_collection.py::Test_genitems::test_example_items1`

**Status:** RESOLVED — the naive string replacement that corrupted parameter values containing `".[["` has been removed. The `getmodpath()` method now correctly preserves parameter values in test names.


## Audit: pytest-dev__pytest-6202

**Patch confirmed live:** `src/_pytest/python.py | 2 +-` (1 insertion, 1 deletion)

### FAIL_TO_PASS
- `testing/test_collection.py::Test_genitems::test_example_items1`: **PASSED** ✓

### PASS_TO_PASS regressions
None — all 73 tests passed.

### Pre-existing (not counted, confirmed against base capture)
- `testing/test_collection.py::TestPrunetraceback::test_collect_report_postprocessing`: XFAIL (exists in baseline, not a regression)

### Kill report
Not applicable — the fix is RESOLVED.

**Gate output summary:** 73 passed, 1 xfailed in 2.72s

All FAIL_TO_PASS tests now pass. Zero PASS_TO_PASS regressions introduced. The patch successfully removed the problematic `.replace(".[", "[")` call from `getmodpath()` in `src/_pytest/python.py:289`, allowing parameter values containing `".[["` to be preserved correctly in test module paths.
