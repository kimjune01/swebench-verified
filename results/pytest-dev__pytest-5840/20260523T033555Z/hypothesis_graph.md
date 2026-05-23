# Hypothesis graph: pytest-dev__pytest-5840

## H₀: Dictionary key type mismatch (abduction, 85%)

**Observation**: Tests fail with `AssertionError: assert PosixPath(...) in {local(...): ...}`

The test creates a `pathlib.Path` key and checks if it exists in `conftest._conftestpath2mod`, but the dictionary contains `py.path.local` keys. Even though both represent the same path string, they have different hash values, causing dictionary lookup to fail.

**Evidence**:
- `py.path.local` and `pathlib.Path` compare equal (`==` returns True) but have different hashes
- Dictionary membership test (`in`) requires both equal hash AND equal value
- Test line 167: `key = Path(str(subconftest)).resolve()` creates pathlib.Path
- Dictionary is populated with py.path.local objects from internal code

**Supporting commit**: fc59e84a0 (testpatch) changed test from `unique_path(subconftest)` to `Path(str(subconftest)).resolve()`, introducing the type mismatch.

**Root cause**: `_conftestpath2mod` dictionary keys are `py.path.local` objects, but external code (tests, users) may attempt lookups with `pathlib.Path` objects. Hash mismatch prevents successful lookup.

**Windows lowercasing issue**: On Windows, `os.path.normcase` lowercases paths (e.g., "Python" → "python"), breaking imports. The `unique_path` function applies `normcase` to all path types, but `pathlib.Path.resolve()` already handles case-insensitive filesystems correctly without lowercasing.

## Gate Loop - /craft iteration 1

**Patch applied:**
- `src/_pytest/config/__init__.py:439`: Added `conftestpath_key = Path(str(conftestpath)).resolve()`
- `src/_pytest/config/__init__.py:441`: Changed dict lookup from `self._conftestpath2mod[conftestpath]` to `self._conftestpath2mod[conftestpath_key]`
- `src/_pytest/config/__init__.py:458`: Changed dict storage from `self._conftestpath2mod[conftestpath] = mod` to `self._conftestpath2mod[conftestpath_key] = mod`

**Gate result:** ✅ PASS
- All 53 tests passed (including both FAIL_TO_PASS tests)
- No regressions
- Test output: `testing/test_conftest.py::test_setinitial_conftest_subdirs[test]` PASSED
- Test output: `testing/test_conftest.py::test_setinitial_conftest_subdirs[tests]` PASSED

**Evidence trajectory:** Convergent success - The fix correctly normalized dictionary keys to `pathlib.Path` objects, allowing lookups with `pathlib.Path` to succeed.

**Resolution:** The recon diagnosis was correct. The issue was that `_conftestpath2mod` used `py.path.local` as keys but was being queried with `pathlib.Path` objects. Normalizing keys to `pathlib.Path` at both storage and lookup points resolved the hash mismatch.

## Audit: pytest-dev__pytest-5840

### FAIL_TO_PASS Results
- `testing/test_conftest.py::test_setinitial_conftest_subdirs[test]`: **PASSED** ✅
- `testing/test_conftest.py::test_setinitial_conftest_subdirs[tests]`: **PASSED** ✅

### PASS_TO_PASS Regressions
None. All 53 tests passed with 1 skipped (case-insensitive filesystem test).

### Pre-existing Failures (not counted, confirmed against base capture)
None.

### Patch Analysis
The craft patch modified `src/_pytest/config/__init__.py` to normalize dictionary keys:
- Line 439: Added `conftestpath_key = Path(str(conftestpath)).resolve()` 
- Line 441: Changed lookup to use `conftestpath_key` instead of `conftestpath`
- Line 458: Changed storage to use `conftestpath_key` instead of `conftestpath`

This resolves the hash mismatch issue where `py.path.local` keys couldn't be found when queried with `pathlib.Path` objects.

### Gate Output Summary
```
======================== 53 passed, 1 skipped in 1.31s =========================
```

All FAIL_TO_PASS tests now pass. Zero regressions introduced. The fix successfully normalizes dictionary keys to `pathlib.Path` objects, allowing consistent lookups regardless of the path type used for querying.

VERDICT: RESOLVED
RE-ENTER: none
