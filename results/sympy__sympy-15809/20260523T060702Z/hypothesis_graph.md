# Hypothesis graph: sympy__sympy-15809

## H₀: Initial Abduction
**Status:** Active  
**Confidence:** Deduction — 99%

The tests fail because `MinMaxBase.__new__` at line 342-343 explicitly raises `ValueError("The Max/Min functions must have arguments.")` when called with zero arguments, preventing the mathematically correct behavior where `Min()` should return infinity and `Max()` should return negative infinity.

**Evidence:**
- `sympy/functions/elementary/miscellaneous.py:343` — raises ValueError for empty args
- `sympy/functions/elementary/miscellaneous.py:361` — existing code already returns `cls.identity` when args is empty after filtering
- `sympy/functions/elementary/miscellaneous.py:743` — `Min.identity = S.Infinity`
- `sympy/functions/elementary/miscellaneous.py:795` — `Max.identity = S.NegativeInfinity`  
- `sympy/functions/elementary/miscellaneous.py:735` — `Max.zero = S.Infinity`
- `sympy/functions/elementary/miscellaneous.py:793` — `Min.zero = S.NegativeInfinity`

**Root cause:** The early guard at line 342-343 prevents the natural flow to line 361 where the identity element would be correctly returned for empty argument lists.

**Fix:** Remove the guard check at lines 342-343. The existing logic already handles zero arguments correctly through the identity element pattern.

## craft gate-loop

### Iteration 1

**Draft**: Removed lines 342-343 from `sympy/functions/elementary/miscellaneous.py` — the early `if not args:` guard that raised ValueError. The existing identity-return logic at line 361 now handles the zero-argument case.

**codex volley**: Confirmed logic is sound. Flagged typo in initial diff (`__assumptions` should be `**assumptions`). Verified no existing tests expect ValueError for zero arguments (all ValueError tests are for complex number arguments).

**Gate result**: ✅ GREEN — all 13 tests passed (test_Min and test_Max now pass, no regressions)

**Resolution**: FAIL_TO_PASS tests pass. Fix complete.

---

## Audit: sympy__sympy-15809

### FAIL_TO_PASS
- test_Min: **PASS** ✓
- test_Max: **PASS** ✓

### PASS_TO_PASS regressions
None — all 10 PASS_TO_PASS tests remain passing.

### Pre-existing failures (not counted)
None.

### Patch applied
```diff
diff --git a/sympy/functions/elementary/miscellaneous.py b/sympy/functions/elementary/miscellaneous.py
index 5f9fe73c5..7f71a3d1b 100644
--- a/sympy/functions/elementary/miscellaneous.py
+++ b/sympy/functions/elementary/miscellaneous.py
@@ -339,9 +339,6 @@ def real_root(arg, n=None, evaluate=None):
 
 class MinMaxBase(Expr, LatticeOp):
     def __new__(cls, *args, **assumptions):
-        if not args:
-            raise ValueError("The Max/Min functions must have arguments.")
-
         args = (sympify(arg) for arg in args)
 
         # first standard filter, for cls.zero and cls.identity
```

The fix removed the early ValueError guard at lines 342-343, allowing the existing identity-return logic at line 361 to handle zero-argument cases correctly:
- `Min()` now returns `S.Infinity` (the identity element for minimum)
- `Max()` now returns `S.NegativeInfinity` (the identity element for maximum)

### Gate output
All 13 tests passed, 1 skipped (numpy not installed):
- test_Min: ok
- test_Max: ok  
- test_minmax_assumptions: ok
- test_issue_8413: ok
- test_root: ok
- test_real_root: ok
- test_rewrite_MaxMin_as_Heaviside: ok
- test_rewrite_MaxMin_as_Piecewise: ok
- test_issue_11099: ok
- test_issue_12638: ok
- test_instantiation_evaluation: ok
- test_rewrite_as_Abs: ok
- test_issue_14000: ok

VERDICT: RESOLVED
RE-ENTER: none
