# Hypothesis graph: pytest-dev__pytest-7236

## H₁: teardown() unconditionally calls _explicit_tearDown for skipped tests (PROPOSED)

**Mode**: deduction  
**Confidence**: 95%

**Observation**: Test `test_pdb_teardown_skipped[@unittest.skip]` fails because tearDown is called on a skipped test when --pdb is used. The `@pytest.mark.skip` variant passes.

**Root cause**: 
In `src/_pytest/unittest.py`:
1. When `--pdb` flag is used, `runtest()` (line 223-224) unconditionally saves `self._testcase.tearDown` to `self._explicit_tearDown` and replaces it with a no-op lambda
2. Later, `teardown()` method (line 124-126) unconditionally calls `self._explicit_tearDown()` if it exists
3. For tests decorated with `@unittest.skip`, the unittest framework skips setUp, the test method, AND tearDown - none are called
4. But pytest's `teardown()` still calls the saved `_explicit_tearDown`, which is incorrect

**Evidence**:
- `src/_pytest/unittest.py:223-224` - `_explicit_tearDown` is set whenever `--pdb` is used, without checking if test will be skipped
- `src/_pytest/unittest.py:124-126` - `_explicit_tearDown()` is called unconditionally
- `src/_pytest/unittest.py:177-182` - When unittest skips a test via `addSkip()`, it sets `self._store[skipped_by_mark_key] = True`
- Standard unittest behavior (verified): `@unittest.skip` decorated tests never call setUp or tearDown
- Test output: `@pytest.mark.skip` variant passes (pytest skip handling prevents setup/runtest), but `@unittest.skip` fails (unittest skip happens inside runtest, after `_explicit_tearDown` is set)

**Edit site**:
`src/_pytest/unittest.py` lines 123-128 - In the `teardown()` method, check if the test was skipped (via `skipped_by_mark_key` in `self._store`) before calling `_explicit_tearDown()`. If skipped, don't call tearDown.

**Code location**:
```python
def teardown(self):
    if self._explicit_tearDown is not None:
        self._explicit_tearDown()  # <-- This should be conditional on not skipped
        self._explicit_tearDown = None
    self._testcase = None
    self._obj = None
```

**Expected fix**:
```python
def teardown(self):
    if self._explicit_tearDown is not None:
        if not self._store.get(skipped_by_mark_key, False):
            self._explicit_tearDown()
        self._explicit_tearDown = None
    self._testcase = None
    self._obj = None
```


## craft gate loop

### Iteration 1: Initial fix

**Approach**: Check for `__unittest_skip__` attribute on test method and test class to distinguish decorator skips from body skips. Only suppress tearDown for decorator skips to match unittest semantics.

**Change applied**:
```python
def teardown(self):
    if self._explicit_tearDown is not None:
        explicit_tearDown = self._explicit_tearDown
        self._explicit_tearDown = None
        # Don't call tearDown for decorator-skipped tests to match unittest behavior
        skip = (
            getattr(self._obj, "__unittest_skip__", False)
            or getattr(self._testcase.__class__, "__unittest_skip__", False)
        )
        if not skip:
            explicit_tearDown()
    self._testcase = None
    self._obj = None
```

**Codex feedback**:
1. First draft had resource leak - needed to clear `_explicit_tearDown` even when skipped
2. Needed to check both method-level and class-level `__unittest_skip__` attributes
3. This approach preserves correct tearDown behavior for body skips (SkipTest raised during test execution)

**Gate result**: ✅ PASS
- `test_pdb_teardown_skipped[@unittest.skip]` - PASSED
- `test_pdb_teardown_skipped[@pytest.mark.skip]` - PASSED
- All 52 tests in test_unittest.py passed

**Trajectory**: Convergent (resolved) - Fix correctly addresses decorator skips without affecting body skips or other tests.

**Resolution**: RESOLVED - The fix matches unittest semantics by detecting decorator-skipped tests and avoiding tearDown calls for them, while still calling tearDown for body-skipped tests as unittest would.

## Audit: pytest-dev__pytest-7236

### FAIL_TO_PASS
- `testing/test_unittest.py::test_pdb_teardown_skipped[@unittest.skip]` → **PASSED** ✅

### PASS_TO_PASS regressions
**None** - All 52 tests passed, 9 skipped (missing optional dependencies: twisted, asynctest).

### Pre-existing (not counted)
**None** - The `AsyncArguments.test_something_async_fails` failure within `test_async_support` is an intentional subtest failure (testing pytest's async error handling) and appears identically in the baseline capture. The outer test `test_async_support` passes correctly.

### Verification
The craft patch successfully:
1. ✅ Fixed the FAIL_TO_PASS test by detecting `__unittest_skip__` attributes on both test methods and test classes
2. ✅ Preserved all PASS_TO_PASS test behavior - no regressions
3. ✅ Matches unittest semantics: decorator-skipped tests skip tearDown, while body-skipped tests (raising SkipTest) still call tearDown

The fix is minimal, correct, and complete.

VERDICT: RESOLVED
RE-ENTER: none
