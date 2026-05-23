# Hypothesis graph: pytest-dev__pytest-7490

## H₀: Tests fail because dynamically added xfail markers are not evaluated (abduction)
**Status**: Initial hypothesis
**Timestamp**: 2026-05-23

The failing tests show:
- `test_dynamic_xfail_set_during_runtest_failed`: expects xfailed=1, got failed=1
- `test_dynamic_xfail_set_during_runtest_passed_strict`: expects failed=1 (strict XPASS), got passed=1

Both tests dynamically add xfail markers during test execution via `request.node.add_marker(pytest.mark.xfail(...))`, but the markers are ignored.

## H₁: Commit c9737ae91 removed post-test xfail re-evaluation (deduction - 95%)
**Status**: Root cause identified
**Evidence**:
- `src/_pytest/skipping.py:247-257` - `pytest_runtest_call` function
- `src/_pytest/skipping.py:260-306` - `pytest_runtest_makereport` function
- Git commit c9737ae91: "skipping: simplify xfail handling during call phase"

**Analysis**:
The old code (pre-c9737ae91) had post-yield xfail re-evaluation in `pytest_runtest_call`:
```python
outcome = yield
passed = outcome.excinfo is None
if passed:
    xfailed = item._store.get(xfailed_key, None)
    if xfailed is None:
        item._store[xfailed_key] = xfailed = evaluate_xfail_marks(item)
```

The new code removed this, relying only on pre-yield evaluation. Markers added during test execution are never picked up.

**Execution timeline**:
1. `pytest_runtest_setup` (line 234): Evaluates xfail marks → None (no marker yet)
2. `pytest_runtest_call` (line 248): Re-evaluates → None (marker not added yet)
3. `yield` (line 255): Test executes, adds marker dynamically
4. After yield: No re-evaluation
5. `pytest_runtest_makereport` (line 263): Reads stored None → marker ignored

**Why test_dynamic_xfail_set_during_funcarg_setup works**:
Fixture setup runs BEFORE `pytest_runtest_call` yields, so the marker is added and picked up by the re-evaluation at line 248-249.

## Root Cause
`pytest_runtest_makereport` reads `xfailed_key` from store (line 263) without re-evaluating. Markers added during test execution (after yield in `pytest_runtest_call`) are never picked up.

## Edit Site
**File**: `src/_pytest/skipping.py`
**Function**: `pytest_runtest_makereport` (lines 260-306)
**Line**: After line 262, before reading xfailed from store
**Change**: Add xfail marker re-evaluation for the "call" phase to catch dynamically added markers

## Gate Loop - Craft Iteration 1

**Action**: Applied fix to re-evaluate xfail marks during call phase in `pytest_runtest_makereport`

**Diff Applied**:
```python
@@ -262,6 +262,9 @@ def pytest_runtest_makereport(item: Item, call: CallInfo[None]):
     outcome = yield
     rep = outcome.get_result()
     xfailed = item._store.get(xfailed_key, None)
+    # Re-evaluate xfail marks for call phase to catch dynamically added markers
+    if call.when == "call" and xfailed is None and not item.config.option.runxfail:
+        item._store[xfailed_key] = xfailed = evaluate_xfail_marks(item)
     # unittest special case, see setting of unexpectedsuccess_key
     if unexpectedsuccess_key in item._store and rep.when == "call":
```

**Codex Review (pre-gate)**: Approved with minor note about redundant line (removed in final version). Confirmed the fix should work for both test cases.

**Gate Result**: ✓ GREEN
- `PASSED testing/test_skipping.py::TestXFail::test_dynamic_xfail_set_during_runtest_failed`
- `PASSED testing/test_skipping.py::TestXFail::test_dynamic_xfail_set_during_runtest_passed_strict`
- All 81 tests in test_skipping.py passed

**Trajectory**: Convergent success (immediate resolution)

**Status**: RESOLVED - Both FAIL_TO_PASS tests pass. The fix correctly handles dynamically added xfail markers by re-evaluating them when `call.when == "call"` in `pytest_runtest_makereport`, before the report outcome is processed.

---

# Audit: pytest-dev__pytest-7490

## FAIL_TO_PASS
- testing/test_skipping.py::TestXFail::test_dynamic_xfail_set_during_runtest_failed: PASS ✓
- testing/test_skipping.py::TestXFail::test_dynamic_xfail_set_during_runtest_passed_strict: PASS ✓

## PASS_TO_PASS regressions
none

## Pre-existing (not counted, confirmed against base capture)
none

## Patch Summary
Added 3 lines to src/_pytest/skipping.py in `pytest_runtest_makereport()`:
- Re-evaluates xfail marks during the call phase when `xfailed` is None
- Catches dynamically added xfail markers set during test execution (e.g., via `request.node.add_marker()`)
- Only applies when `call.when == "call"` and `runxfail` option is not set

## Gate Results
All 81 tests in testing/test_skipping.py passed. No failures, no regressions.

VERDICT: RESOLVED
RE-ENTER: none
