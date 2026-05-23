# Hypothesis graph: matplotlib__matplotlib-23299

## H₀: Backend restoration in rc_context triggers figure destruction
**Mode**: Deduction  
**Confidence**: 95%

When `rc_context()` exits, it restores ALL rcParams including 'backend'. If the original backend was the auto-backend sentinel, restoring it causes the next access to `rcParams['backend']` (e.g., via `get_backend()`) to trigger `switch_backend()`, which calls `close("all")` and destroys all figures.

**Evidence trail**:
1. `lib/matplotlib/__init__.py:1096` - rc_context finally block: `dict.update(rcParams, orig)` restores all params
2. `lib/matplotlib/__init__.py:665-669` - RcParams.__getitem__ detects auto sentinel and triggers switch_backend
3. `lib/matplotlib/pyplot.py:225` - switch_backend calls `close("all")` 
4. `lib/matplotlib/style/core.py:40-43` - STYLE_BLACKLIST includes 'backend', indicating it should not be temporarily modified

**Root cause**: rc_context does not respect STYLE_BLACKLIST when restoring parameters. Backend should persist across rc_context boundaries because backend switching has persistent side effects.

**Supporting quotes**:
- `lib/matplotlib/__init__.py:1096`: `dict.update(rcParams, orig)  # Revert to the original rcs.`
- `lib/matplotlib/style/core.py:41`: `STYLE_BLACKLIST = {'interactive', 'backend', 'webagg.port', ...}`
- `lib/matplotlib/__init__.py:665-669`: 
  ```python
  elif key == "backend" and self is globals().get("rcParams"):
      val = dict.__getitem__(self, key)
      if val is rcsetup._auto_backend_sentinel:
          from matplotlib import pyplot as plt
          plt.switch_backend(rcsetup._auto_backend_sentinel)
  ```


## Craft Gate Loop

### Iteration 1: Initial fix attempt (FAILED - KeyError)
**Hypothesis**: Import STYLE_BLACKLIST and filter it from restoration
**Diff**: Added import, used `orig.pop('backend', None)` after copy
**Gate result**: KeyError during test fixture setup
**Trajectory**: Divergent (new error)
**Analysis**: `RcParams.copy()` returns RcParams object with special __getitem__ behavior. The pop() operation triggered KeyError despite default argument, likely due to special backend handling during copy.

### Iteration 2: Revised to dict+del (FAILED - same issue)
**Hypothesis**: Use dict() wrapper to avoid RcParams special behavior
**Diff**: `orig = dict(rcParams.copy()); del orig['backend']`
**Gate result**: Same KeyError 
**Trajectory**: Convergent-stuck
**Codex feedback**: Still accessing 'backend' through special __getitem__ before deletion. Should exclude during snapshot construction, not after.

### Iteration 3: Exclude during construction (PASSED)
**Hypothesis**: Build snapshot while excluding 'backend' from the start
**Diff**: `orig = {k: rcParams[k] for k in rcParams if k != "backend"}`
**Gate result**: test_no_backend_reset_rccontext PASSED
**Other failures**: test_rcparams_update and test_rcparams_init also failed, but these are pre-existing baseline failures (verified by reverting fix and re-running gate - they fail without the fix too)
**Resolution**: FAIL_TO_PASS test now passes. The 2 other failures are not regressions.

## Final fix
Changed line 1090 of lib/matplotlib/__init__.py from:
```python
orig = rcParams.copy()
```
to:
```python
orig = {k: rcParams[k] for k in rcParams if k != "backend"}
```

This excludes 'backend' from the snapshot during construction, avoiding both:
1. Triggering special backend __getitem__ behavior during copy
2. Restoring 'backend' in the finally block, which allows backend changes inside rc_context to persist

**Status**: RESOLVED - FAIL_TO_PASS test passes, no new regressions introduced

---

# Audit: matplotlib__matplotlib-23299

## FAIL_TO_PASS
- test_no_backend_reset_rccontext: **PASSED** ✓

## PASS_TO_PASS regressions
- **test_rcparams_update**: Failed - DID NOT WARN. Expected UserWarning with "validate" message during validation failure, but no warnings emitted
- **test_rcparams_init**: Failed - DID NOT WARN. Expected UserWarning with "validate" message during validation failure, but no warnings emitted

## Pre-existing (not counted, confirmed against base capture)
- none

## Kill report

**Regressions**: Two PASS_TO_PASS tests (`test_rcparams_update` and `test_rcparams_init`) are failing. Both tests expect a UserWarning to be emitted when RcParams validation fails, but no warning is being emitted.

**Error details**:
- Both tests use `pytest.warns(UserWarning, match="validate")` expecting a warning during validation failure
- The ValueError is being raised correctly at `lib/matplotlib/__init__.py:651`
- But the expected UserWarning is not being emitted

**Analysis**: The patch only modifies `rc_context()` (line 1090), changing from `rcParams.copy()` to a dict comprehension that excludes 'backend'. However, this change should not affect `RcParams.__setitem__` behavior, which is what these tests exercise.

**Likely cause**: The failing tests don't use `rc_context()` directly, suggesting either:
1. The patch has an unexpected side effect on module initialization
2. There's import-time code that uses `rc_context()` and affects warning behavior
3. Craft's earlier claim that these were "pre-existing baseline failures" may have been correct, but they're not visible in the provided base capture (which was truncated)

**Cross-check needed**: The base capture provided doesn't show these tests as failures (no FAILED section visible in output), but craft's hypothesis graph claims they were pre-existing. This discrepancy suggests the base capture may be incomplete.

**Route recommendation**: RE-ENTER craft to narrow the fix or investigate the warning emission issue. However, if these tests were actually pre-existing failures that craft already verified, the gate harness should have that data.

VERDICT: NOT_RESOLVED — regressions
RE-ENTER: craft

## Craft: Implementation

### Gate iteration 1 (divergent - audit re-entry)

**Change**: Modified line 1090 from `orig = rcParams.copy()` to `orig = {k: v for k, v in rcParams.items() if k != "backend"}`. This excludes backend from the snapshot so it persists across rc_context boundaries.

**Codex volley 1**: codex initially suggested using STYLE_BLACKLIST (following recon's recommendation), but then reconsidered and said STYLE_BLACKLIST is for style sheets, not rc_context. Only backend should persist due to persistent side effects (module loading, GUI loops). Other blacklisted params like 'interactive', 'toolbar' should restore normally in a temporary context.

**Codex volley 2**: codex approved backend-only exclusion approach. Key insight: use `.items()` instead of `__getitem__` access to avoid side effects during snapshot.

**Gate result**: 
- FAIL_TO_PASS test `test_no_backend_reset_rccontext`: **PASSED** ✓
- Two PASS_TO_PASS failures noted: `test_rcparams_update` and `test_rcparams_init`

**Pre-existing verification**: Stashed changes and confirmed both "regressed" tests FAIL in base state. These are pre-existing failures unrelated to the fix. The audit report noted this possibility: "These may be pre-existing failures... but the provided base capture is truncated."

**Final state**: Working tree contains the minimal fix that makes FAIL_TO_PASS pass without introducing new regressions.

**Resolution**: The fix correctly makes backend persist across rc_context by excluding it from the snapshot. codex's insight about STYLE_BLACKLIST being the wrong abstraction was correct - backend is special due to persistent side effects, not because it's in a style blacklist.

---

# Audit: matplotlib__matplotlib-23299 (Final Verification)

## Phase 1: Patch confirmation
```
 lib/matplotlib/__init__.py | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```
Patch is live: line 1090 changed from `orig = rcParams.copy()` to `orig = {k: v for k, v in rcParams.items() if k != "backend"}`

## Phase 2: Gate results
Full test suite run completed in 2.29s:
- 205 tests PASSED
- 2 tests FAILED
- 1 test SKIPPED

## Phase 3: Classification against baseline

### FAIL_TO_PASS
- `test_no_backend_reset_rccontext`: **PASSED** ✓

### PASS_TO_PASS — Suspected regressions (verified against base)
- `test_rcparams_update`: FAILED (DID NOT WARN — expects UserWarning with "validate")
- `test_rcparams_init`: FAILED (DID NOT WARN — expects UserWarning with "validate")

**Base verification**: Stashed patch and ran both tests on clean base:
- `test_rcparams_update` on base: **FAILED** with identical error
- `test_rcparams_init` on base: **FAILED** with identical error

Both failures are **pre-existing** — they were already broken before the patch.

### Pre-existing (not counted, confirmed against base capture)
- `test_rcparams_update` — Both base and patched fail with "DID NOT WARN" error
- `test_rcparams_init` — Both base and patched fail with "DID NOT WARN" error

## Phase 4: Verdict

✅ All FAIL_TO_PASS tests pass (1/1)
✅ Zero PASS_TO_PASS regressions introduced
✅ Two failures are pre-existing (verified by running on base)

The patch correctly excludes 'backend' from rc_context's snapshot, preventing backend restoration from triggering figure destruction. The fix is minimal, targeted, and introduces no new failures.

VERDICT: RESOLVED
RE-ENTER: none
