# Hypothesis graph: sympy__sympy-11618

## H0: Initial Abduction (Phase 1)
**Status**: ACTIVE
**Confidence**: 95% (deduction - traced code execution)

The test `test_issue_11617` fails because Point3D(1,0,2).distance(Point2D(2,0)) returns 1 instead of sqrt(5).

**Root Cause**: The `distance` method in the Point class (sympy/geometry/point.py:269-270) uses Python's built-in `zip()` function to pair coordinates from two points. The `zip()` function stops when the shortest iterable is exhausted, silently dropping the third coordinate (z=2) from Point3D when paired with Point2D.

**Code Path**:
1. Test calls `p1.distance(p2)` where p1=Point3D(1,0,2), p2=Point2D(2,0)
2. Method at line 269: `zip(self.args, p.args)` produces [(1,2), (0,0)] - drops the (2,) third coordinate
3. Distance calculated as sqrt((1-2)^2 + (0-0)^2) = 1, not sqrt((1-2)^2 + (0-0)^2 + (2-0)^2) = sqrt(5)

**Supporting Evidence**:
- sympy/geometry/point.py:269-270: Uses `zip(self.args, p.args if isinstance(p, Point) else p)`
- Verified with test: `list(zip((1,0,2), (2,0))) == [(1,2), (0,0)]` - third pair missing

**Fix**: Replace `zip` with `zip_longest` (fillvalue=0) from sympy.core.compatibility to treat missing coordinates as zero, which is the mathematically correct behavior for Euclidean distance in spaces of different dimensions.

**Edit Sites**:
1. sympy/geometry/point.py:3 - Add `zip_longest` to import from `sympy.core.compatibility`
2. sympy/geometry/point.py:269-270 - Replace `zip(` with `zip_longest(` and add `, fillvalue=0)` before closing paren

**Related Methods** (same structural issue, but not covered by failing test):
- taxicab_distance (line 303)
- midpoint (line 332)
- dot (line 409)
Note: equals (line 416) and __add__ (line 446) are safe - they check len() before using zip


## Craft: Gate Loop

### Iteration 1

**Hypothesis**: Replace `zip()` with `zip_longest(fillvalue=0)` in the `distance` method to avoid truncating coordinates when comparing points of different dimensions.

**Edit sites**:
1. Line 14: Add `zip_longest` to imports
2. Lines 269-270: Replace `zip` with `zip_longest(..., fillvalue=0)`

**Diff applied**:
```diff
--- a/sympy/geometry/point.py
+++ b/sympy/geometry/point.py
@@ -11,7 +11,7 @@
 from __future__ import division, print_function
 
 from sympy.core import S, sympify
-from sympy.core.compatibility import iterable
+from sympy.core.compatibility import iterable, zip_longest
 from sympy.core.containers import Tuple
 from sympy.simplify import nsimplify, simplify
 from sympy.geometry.exceptions import GeometryError
@@ -266,8 +266,8 @@ def distance(self, p):
         sqrt(x**2 + y**2)
 
         """
-        return sqrt(sum([(a - b)**2 for a, b in zip(
-            self.args, p.args if isinstance(p, Point) else p)]))
+        return sqrt(sum([(a - b)**2 for a, b in zip_longest(
+            self.args, p.args if isinstance(p, Point) else p, fillvalue=0)]))
```

**Gate result**: ✅ PASS
- 6 tests passed (up from 5 on baseline)
- 0 tests failed (test_issue_11617 now passes)
- 1 exception (pre-existing, not introduced by this fix)

**Trajectory**: Convergent success - FAIL_TO_PASS test `test_issue_11617` now passes.

**Manual verification**:
```python
Point3D(1,0,2).distance(Point2D(2,0)) == sqrt(5)  # ✅ True
```

**Notes**:
- Tried `fillvalue=S.Zero` first (per codex style suggestion) but caused RecursionError
- Reverted to `fillvalue=0` - works correctly
- The exception in gate is pre-existing (also present on baseline before our fix)

## Audit: sympy__sympy-11618

### Test Results

**FAIL_TO_PASS**:
- test_issue_11617: ✅ PASS

**PASS_TO_PASS**:
- test_point3D: ✅ PASS
- test_Point2D: ✅ PASS
- test_issue_9214: ✅ PASS
- test_transform: ✅ PASS

**PASS_TO_PASS regressions**: none

**Pre-existing failures** (confirmed against base capture, not counted):
- One test with RecursionError in `_eval_is_prime` (sympy/core/mul.py:1296) - identical to baseline

### Classification

✅ All FAIL_TO_PASS tests pass: YES (1/1)
✅ Zero PASS_TO_PASS regressions: YES (4/4 pass)
✅ Pre-existing failures excluded: 1 exception present in both baseline and patched runs

### Gate Output Summary
- Tests finished: 6 passed, 1 exception
- The exception is pre-existing (RecursionError in assumptions system, not related to Point.distance)
- All contract tests (F2P + P2P) pass

VERDICT: RESOLVED
RE-ENTER: none
