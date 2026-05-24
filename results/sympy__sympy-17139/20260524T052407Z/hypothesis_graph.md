# Hypothesis graph: sympy__sympy-17139

## H₀: Invalid comparison of complex exponents (ABDUCTION)

**Status**: Active hypothesis  
**Confidence**: Deduction — 95%

**Observation**: Both `test__TR56` and `test_issue_17137` fail with:
```
File "/testbed/sympy/simplify/fu.py", line 504, in _f
    if (rv.exp < 0) == True:
File "/testbed/sympy/core/expr.py", line 406, in __lt__
    raise TypeError("Invalid comparison of complex %s" % me)
TypeError: Invalid comparison of complex I
```

**Root cause**: The `_TR56` helper function at `sympy/simplify/fu.py:500-524` performs direct numerical comparisons on exponents without checking if they are real numbers:
- Line 504: `if (rv.exp < 0) == True:`
- Line 506: `if (rv.exp > max) == True:`

When `rv.exp` is complex (e.g., `I` or `2 + 3*I`), the comparison operator raises `TypeError` because complex numbers lack a total ordering.

**Evidence**:
- `fu.py:504` — `if (rv.exp < 0) == True:` (unsafe comparison)
- `fu.py:506` — `if (rv.exp > max) == True:` (unsafe comparison)
- `fu.py:633` — `a.is_Pow and a.exp.is_Integer and a.exp > 0` (correct pattern: check type before comparing)
- Tests expect: `simplify(cos(x)**I) == cos(x)**I` (return unchanged)

**Diagnosis**: The function is designed for real integer exponents (transforms like `sin(x)**6 -> (1 - cos(x)**2)**3`). It should skip complex exponents but instead crashes on comparison.

**Edit sites**:
- `sympy/simplify/fu.py:500-507` — Add early return if `rv.exp` is not real/numeric before the comparison lines

**Fix approach**: Check if `rv.exp.is_real is False` or `rv.exp.is_number is False`, and if so, return `rv` unchanged. This makes the function skip complex exponents safely.


## Craft gate loop

### Iteration 1: Initial fix with is_real guard

**Hypothesis**: Adding `if rv.exp.is_real is not True: return rv` guard after line 502 in `_TR56._f()` will prevent complex exponent comparisons and make FAIL_TO_PASS tests pass.

**Applied diff**:
```diff
--- a/sympy/simplify/fu.py
+++ b/sympy/simplify/fu.py
@@ -501,6 +501,9 @@ def _TR56(rv, f, g, h, max, pow):
         if not (rv.is_Pow and rv.base.func == f):
             return rv
 
+        if rv.exp.is_real is not True:
+            return rv
+
         if (rv.exp < 0) == True:
             return rv
         if (rv.exp > max) == True:
```

**codex feedback**: 
- First volley: Guard is too broad with `or not rv.exp.is_number`; should use `is_real is not True` instead
- Second volley: Suggests `is_Integer is not True` would be more correct given integer operations in the code, but acknowledges `is_real` addresses the complex/unknown-real concern

**Gate result**: ✅ **PASS**
- test__TR56: ok
- test_issue_17137: ok
- All 71 tests passed, 2 expected to fail

**Trajectory**: Convergent success - FAIL_TO_PASS tests pass, no regressions


---

## Audit: sympy__sympy-17139

### FAIL_TO_PASS results
- test__TR56: **PASS** ✓
- test_issue_17137: **PASS** ✓

### PASS_TO_PASS regressions
None

### Pre-existing failures (confirmed against base capture, not counted)
- test_factorial_simplify: expected to fail (marked 'f' on both base and patched)
- test_simplify_float_vs_integer: expected to fail (marked 'f' on both base and patched)

### Summary
The patch successfully fixes both failing tests by adding an early-return guard that checks `if rv.exp.is_real is not True` before attempting numerical comparisons. This prevents the `TypeError: Invalid comparison of complex I` that was occurring when functions like `cos(x)**I` were being simplified.

**Patch applied**:
```diff
+        if rv.exp.is_real is not True:
+            return rv
+
         if (rv.exp < 0) == True:
```

The fix is minimal, targeted, and introduces zero regressions across the 71-test suite.

