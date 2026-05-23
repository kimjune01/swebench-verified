# Hypothesis graph: pytest-dev__pytest-7571

## Hypothesis Node: Initial Diagnosis

**Type**: abduction
**Confidence**: 95% (deduction - traced through code)

**Observation**: test_change_level_undos_handler_level fails because caplog.handler.level is not restored to 0 after set_level is called.

**Root Cause**: 
- `LogCaptureFixture.set_level()` (line 425-437) changes both logger level AND handler level
- It saves the initial logger level to `self._initial_logger_levels` for restoration
- But it does NOT save the initial handler level
- `LogCaptureFixture._finalize()` (line 351-359) only restores logger levels from `self._initial_logger_levels`
- The handler level is never restored, so it persists across tests
- The handler is shared across all tests (created once in LoggingPlugin.__init__)

**Supporting Evidence**:
- `src/_pytest/logging.py:437` - `self.handler.setLevel(level)` changes handler level
- `src/_pytest/logging.py:434` - `self._initial_logger_levels.setdefault(logger, logger_obj.level)` only saves logger level
- `src/_pytest/logging.py:357-359` - `_finalize` only restores logger levels
- `src/_pytest/logging.py:452-458` - `at_level` context manager shows correct pattern: saves handler level at 452, restores at 458

**Fix Required**:
1. Add field to store initial handler level (like _initial_logger_levels)
2. Save handler level before changing it in set_level
3. Restore handler level in _finalize


## craft gate loop

### Iteration 1 (PASS)

**Action**: Applied minimal fix to track and restore handler level:
- Added `_initial_handler_level` field to `LogCaptureFixture.__init__`
- Save handler level in `set_level` before first change
- Restore handler level in `_finalize`

**Codex review**: No structural issues. Logic is sound. Sentinel pattern acceptable.

**Gate result**: ✅ PASS
- `test_change_level_undos_handler_level` PASSED
- All 15 fixture tests PASSED

**Resolution**: Handler level now properly restored between tests, matching the pattern in `at_level` context manager.

## Audit: pytest-dev__pytest-7571

### Patch Verification
✅ Patch is live in tree (src/_pytest/logging.py, 7 insertions)

### Gate Results

**FAIL_TO_PASS:**
- testing/logging/test_fixture.py::test_change_level_undos_handler_level: **PASSED** ✓

**PASS_TO_PASS (15 tests):**
- testing/logging/test_fixture.py::test_change_level: **PASSED** ✓
- testing/logging/test_fixture.py::test_with_statement: **PASSED** ✓
- testing/logging/test_fixture.py::test_log_access: **PASSED** ✓
- testing/logging/test_fixture.py::test_messages: **PASSED** ✓
- testing/logging/test_fixture.py::test_record_tuples: **PASSED** ✓
- testing/logging/test_fixture.py::test_unicode: **PASSED** ✓
- testing/logging/test_fixture.py::test_clear: **PASSED** ✓
- testing/logging/test_fixture.py::test_caplog_captures_for_all_stages: **PASSED** ✓
- testing/logging/test_fixture.py::test_fixture_help: **PASSED** ✓
- testing/logging/test_fixture.py::test_change_level_undo: **PASSED** ✓
- testing/logging/test_fixture.py::test_ini_controls_global_log_level: **PASSED** ✓
- testing/logging/test_fixture.py::test_caplog_can_override_global_log_level: **PASSED** ✓
- testing/logging/test_fixture.py::test_caplog_captures_despite_exception: **PASSED** ✓
- testing/logging/test_fixture.py::test_log_report_captures_according_to_config_option_upon_failure: **PASSED** ✓

### Classification

**PASS_TO_PASS regressions:** None

**Pre-existing failures (not counted):** 
The gate output shows nested test failures in pytester sub-runs, which match the fail-on-base capture exactly:
- test_caplog_captures_despite_exception (nested): Expected failure (raises Exception) - confirmed on base
- test_log_report_captures_according_to_config_option_upon_failure (nested): Expected failure (assert False) - confirmed on base

These are pytester tests that intentionally run failing sub-tests to verify pytest's behavior on test failure. They are not regressions.

### Contract Verification
✅ All FAIL_TO_PASS tests now pass (1/1)
✅ Zero PASS_TO_PASS regressions (0/14)
✅ All 15 tests in testing/logging/test_fixture.py PASSED

### Summary
The patch successfully restores handler level after `set_level()` calls by:
1. Tracking initial handler level in `_initial_handler_level` 
2. Capturing it on first `set_level()` call
3. Restoring it in `_finalize()`

This mirrors the pattern already used in the `at_level()` context manager and resolves the issue without introducing regressions.

