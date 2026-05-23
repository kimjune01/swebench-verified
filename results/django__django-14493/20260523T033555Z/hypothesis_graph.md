# Hypothesis graph: django__django-14493
# Hypothesis Graph: django__django-14493

## H0 (abduction, baseline)
**Claim:** The test fails because `substitutions` is referenced before assignment when `max_post_process_passes = 0`.

**Evidence:**
- Error message: `UnboundLocalError: local variable 'substitutions' referenced before assignment`
- Stack trace points to `django/contrib/staticfiles/storage.py:274`

**Mode:** abduction (pattern recognition from error message)
**Confidence:** 60%

## H1 (deduction, localized root cause)
**Claim:** In `HashedFilesMixin.post_process()`, the variable `substitutions` is only initialized inside the `for i in range(self.max_post_process_passes):` loop (line 265), but is referenced after the loop (line 274). When `max_post_process_passes = 0`, the loop body never executes, leaving `substitutions` uninitialized.

**Evidence:**
- `django/contrib/staticfiles/storage.py:264`: `for i in range(self.max_post_process_passes):`
- `django/contrib/staticfiles/storage.py:265`: `    substitutions = False` (only set inside loop)
- `django/contrib/staticfiles/storage.py:274`: `if substitutions:` (referenced outside loop)
- When `max_post_process_passes = 0`, `range(0)` produces empty sequence, loop never executes
- Git blame shows lines 264-274 introduced in commit 53bffe8d03 (Fixed #24452, 2017-01-11)

**Mode:** deduction (traced code flow, identified control flow bug)
**Confidence:** 99%

## Edit sites identified
1. `django/contrib/staticfiles/storage.py` line 264-265: Initialize `substitutions = False` BEFORE the for loop, not inside it
   - Current: `for i in range(...):\n    substitutions = False`
   - Required: `substitutions = False\nfor i in range(...):`

## Craft gate loop

### Iteration 1: Draft and volley

**Initial draft:** Move `substitutions = False` from inside the loop to before it.

**Codex feedback:** The initial draft broke convergence detection. Once `substitutions` becomes True in any pass, it would stay True forever because of `substitutions = substitutions or subst`, preventing the break condition from working on subsequent passes.

**Revised fix:** Add `substitutions = False` BEFORE the loop (fixes UnboundLocalError when max_post_process_passes = 0) while keeping the existing initialization INSIDE the loop (preserves per-pass convergence detection).

Applied fix to `django/contrib/staticfiles/storage.py` line 264:
- Added: `substitutions = False` before the for loop
- Kept: `substitutions = False` at start of each iteration

**Gate result:** ✓ GREEN - All 37 tests passed, including `test_collectstatistic_no_post_process_replaced_paths`

**Resolution:** FAIL_TO_PASS test passes with no regressions.

---

# Audit: django__django-14493

## Patch verification
Patch is live: `django/contrib/staticfiles/storage.py` (+1 line)
- Added `substitutions = False` before the for loop at line 264

## Gate results
Ran 37 tests in 0.670s — **OK**

## FAIL_TO_PASS
- `test_collectstatistic_no_post_process_replaced_paths`: **PASS** ✓

## PASS_TO_PASS regressions
None — all 36 PASS_TO_PASS tests remain passing.

## Pre-existing failures (not counted)
None.

## Conclusion
The fix successfully resolves the UnboundLocalError when `max_post_process_passes = 0`. Initializing `substitutions = False` before the loop ensures the variable is defined even when the loop body never executes, while the existing in-loop initialization preserves per-pass convergence detection.
