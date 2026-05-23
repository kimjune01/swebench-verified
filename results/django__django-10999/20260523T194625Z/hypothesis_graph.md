# Hypothesis graph: django__django-10999

## H0: Baseline (abduction)

**Date**: 2026-05-23
**Status**: Initial diagnosis
**Confidence**: 85% (abduction)

The tests fail because:
1. The regex lookahead `(?=\d+:\d+)` on line 32 doesn't allow negative components, preventing proper matching
2. The parsing logic doesn't propagate a leading negative sign to subsequent unsigned components

**Failing test patterns**:
- `-15:30` parses as minutes=-15, seconds=30 → actual: timedelta(-1, 85530) vs expected: timedelta(-1, 85470)
- `-1:15:30` parses as hours=-1, minutes=15, seconds=30 → actual: timedelta(-1, 83730) vs expected: timedelta(-1, 81870)
- `-01:-01` parses as minutes=-1, seconds=-1 → actual: timedelta(-1, 86339) vs expected: None

**Root cause**: 
When a duration string has a leading negative component (e.g., `-1:15:30`), the regex captures only the first component as negative while subsequent components are captured as positive. The `float()` conversion preserves signs correctly, but `timedelta(hours=-1, minutes=15, seconds=30)` computes as -3600 + 900 + 30 = -2670 seconds, not the intended -3600 - 900 - 30 = -4530 seconds.

**Evidence**:
- `django/utils/dateparse.py:32` - lookahead pattern `(?=\d+:\d+)` requires positive-only components
- `django/utils/dateparse.py:145` - no logic to propagate negative signs across components (unlike microseconds at line 143-144)


---

## Craft Implementation (Gate Loop)

### Iteration 1: Draft & Volley

**Initial draft**: Added both regex lookahead change `(?=-?\d+:-?\d+)` and sign propagation logic.

**codex feedback**: 
- Regex change unnecessary - existing `(?=\d+:\d+)` already captures `-1:15:30` correctly
- Regex change makes parser too permissive, accepting invalid mixed-sign formats like `1:-15:30`
- Validation logic flawed - only rejected multiple negatives, not mixed signs (e.g., `01:-01` with positive first, negative second)
- Recommended: Keep original lookahead, use cleaner validation: only first present component can have `-`, reject if any later component has explicit `-`, propagate first component's sign to all subsequent unsigned components

**Revision**: Removed regex change, applied codex's cleaner logic.

### Iteration 1: Gate Result

**Status**: ✅ PASS

All 12 tests passed including FAIL_TO_PASS:
- `test_negative` - all negative duration cases now parse correctly
- `test_parse_postgresql_format` - PostgreSQL format cases pass

**Fix applied**:
- Added validation logic after microseconds handling (line ~144)
- Identifies present components (hours/minutes/seconds)
- Rejects if any component after the first has explicit negative sign
- Propagates first component's negative sign to all subsequent unsigned components

**Resolution**: The root cause was correct - lack of sign propagation logic. The fix required only parsing logic changes, not regex modifications.

---

## Audit: django__django-10999

**Date**: 2026-05-23

### FAIL_TO_PASS
- `test_negative`: ✅ PASS (was FAIL on base with 5 sub-test failures)
- `test_parse_postgresql_format`: ✅ PASS

### PASS_TO_PASS regressions
None - all 10 PASS_TO_PASS tests still pass.

### Pre-existing failures
None (confirmed against base capture).

### Gate result
All 12 tests pass. Zero regressions.

**Patch summary**:
- Added validation to reject invalid mixed-sign formats (e.g., `01:-01`)
- Added logic to propagate first component's negative sign to all subsequent unsigned components
- 15 lines added to `django/utils/dateparse.py` after microseconds handling

**VERDICT**: RESOLVED
**RE-ENTER**: none

