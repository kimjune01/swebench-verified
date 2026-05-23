# Hypothesis graph: pytest-dev__pytest-10051

## H₀ (abduction): Test failure baseline
**Status**: Confirmed  
**Evidence**: `/tmp/gate-pytest-dev_pytest-10051` output

The test `test_clear_for_call_stage` fails because after calling `caplog.clear()`, `caplog.get_records("call")` returns the old log records `[<LogRecord: ..."a_call_log">]` instead of an empty list `[]`.

```
assert caplog.get_records("call") == []
E       assert [<LogRecord: ..."a_call_log">] == []
```

## H₁ (deduction): Root cause - list reference decoupling
**Status**: Active  
**Confidence**: 95% (deduction - traced through code)

### The problem

`caplog.get_records(when)` becomes decoupled from `handler.records` when `caplog.clear()` is called.

**Call path**:
1. During test setup/call/teardown phases, `_runtest_for()` in `src/_pytest/logging.py:687` executes:
   - Line 697: `caplog_handler.reset()` - creates a NEW empty list
   - Line 699: `item.stash[caplog_records_key][when] = caplog_handler.records` - stores a REFERENCE to the handler's list

2. When user calls `caplog.clear()` (line 441), it calls:
   - Line 443: `self.handler.reset()`

3. `LogCaptureHandler.reset()` (line 345) does:
   ```python
   self.records = []  # Creates a NEW list object
   self.stream = StringIO()
   ```

4. When `caplog.get_records(when)` is called (line 388):
   ```python
   return self._item.stash[caplog_records_key].get(when, [])
   ```
   It returns the OLD list from the stash, not the handler's NEW empty list.

**Why this breaks**:
- The stash stores a reference to the original list created during phase setup
- `reset()` creates a completely new list and assigns it to `handler.records`
- The stash still points to the old list (now orphaned)
- New log records go into the new list
- `get_records()` returns the old list (frozen with old records)

### Supporting evidence
- `src/_pytest/logging.py:345-347`: `reset()` assigns new list instead of clearing in-place
- `src/_pytest/logging.py:699`: Stash stores reference to handler.records
- `src/_pytest/logging.py:399`: `get_records()` reads from stash, not handler

### Edit sites

**File**: `src/_pytest/logging.py`
**Location**: Lines 441-443 (LogCaptureFixture.clear method)

**Change needed**: Clear the handler's records list in-place instead of calling reset(), which creates a new list. Must also reset the stream to clear the captured text.

**Current code**:
```python
def clear(self) -> None:
    """Reset the list of log records and the captured log text."""
    self.handler.reset()
```

**Fix**: Replace with in-place clearing:
```python
def clear(self) -> None:
    """Reset the list of log records and the captured log text."""
    self.handler.records.clear()  # Clear in-place to maintain stash reference
    self.handler.stream = StringIO()  # Reset the text stream
```

**Why this works**:
- `handler.records.clear()` empties the list without creating a new object
- The stash reference remains valid and points to the now-empty list
- New records append to the same list object
- `get_records(when)` returns the stash reference, which reflects current state
- Other stage records (e.g., "setup") remain untouched
- The stream reset ensures `caplog.text` is also cleared

**Why we don't change `reset()` itself**:
- `reset()` is also called at the START of each test phase (setup/call/teardown)
- At phase boundaries, we WANT a new list so each phase has independent records
- Only user-initiated `clear()` needs in-place clearing

### Verification
This fix would satisfy both existing tests:
1. `test_clear()`: Expects `caplog.records` and `caplog.text` to be empty after clear() ✓
2. `test_clear_for_call_stage()`: Expects `get_records("call")` to be empty after clear(), but `get_records("setup")` to retain setup logs ✓

## Rejected hypotheses
None - first pass diagnosis.

## Open questions
None - the root cause and fix are clear from code inspection.

## Gate Loop: /craft iteration 1

**Hypothesis**: The recon diagnosis is correct — `LogCaptureFixture.clear()` creates a new list via `handler.reset()`, orphaning the stash reference. Fix by clearing in-place.

**Edit applied**:
```diff
--- a/src/_pytest/logging.py
+++ b/src/_pytest/logging.py
@@ -440,7 +440,8 @@ class LogCaptureFixture:
 
     def clear(self) -> None:
         """Reset the list of log records and the captured log text."""
-        self.handler.reset()
+        self.handler.records.clear()
+        self.handler.stream = StringIO()
```

**Codex volley**:
- Initial suggestion: Fix `reset()` itself to preserve list identity
- Counter-evidence: `reset()` is called at phase boundaries where new list objects are intentional (setup→call→teardown phase separation)
- After showing phase boundary code: codex confirmed the original approach is correct

**Gate result**: ✅ PASSED
- `test_clear_for_call_stage` now passes
- All 16 tests in test_fixture.py passed
- No regressions observed

**Trajectory**: Convergent success on first iteration

---

# Audit: pytest-dev__pytest-10051

## FAIL_TO_PASS
- `testing/logging/test_fixture.py::test_clear_for_call_stage`: **PASS** ✓

## PASS_TO_PASS regressions
None — all 16 tests in the PASS_TO_PASS contract passed.

## Pre-existing (not counted, confirmed against base capture)
- `test_caplog_captures_despite_exception` — fails with `Exception` in both baseline and current run
- `test_log_report_captures_according_to_config_option_upon_failure` — fails with `assert False` in both baseline and current run

These failures appear in the fail-on-base capture output provided by the adapter, confirming they existed before the patch was applied.

## Verdict details

The craft patch successfully resolved the issue:
- The target test `test_clear_for_call_stage` now passes (was failing before)
- All PASS_TO_PASS tests remain passing
- No new regressions introduced
- The fix correctly clears log records in-place while preserving the stash reference integrity

**Patch**: 3-line change in `src/_pytest/logging.py` replacing `self.handler.reset()` with in-place clearing (`self.handler.records.clear()` + `self.handler.stream = StringIO()`) in the `LogCaptureFixture.clear()` method.

VERDICT: RESOLVED
RE-ENTER: none
