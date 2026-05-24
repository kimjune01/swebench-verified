# Hypothesis graph: sympy__sympy-15349

## H0 - Sign error in rotation matrix formula (ABDUCTION)
**Status**: Active  
**Confidence**: 95% (deduction from code inspection and manual verification)

**Observation**: Tests fail because `to_rotation_matrix()` returns incorrect values. For `q = Quaternion(cos(x/2), sin(x/2), 0, 0)`, the method returns:
```
Matrix([[1, 0, 0], [0, cos(x), sin(x)], [0, sin(x), cos(x)]])
```
But should return:
```
Matrix([[1, 0, 0], [0, cos(x), -sin(x)], [0, sin(x), cos(x)]])
```

**Root cause**: Line 532 in `sympy/algebras/quaternion.py` has incorrect sign:
```python
m12 = 2*s*(q.c*q.d + q.b*q.a)  # WRONG: should be minus
```

According to Wikipedia reference (mentioned in test), the correct formula for quaternion rotation matrix element at position [1,2] is `2(yz - xw)` where (w,x,y,z) are quaternion components. In the code, this maps to `2*s*(q.c*q.d - q.b*q.a)`.

**Verification**:
- For q=(1,2,3,4), current m12 = 2/30*(12+2) = 14/15, but test expects 2/3 = 2/30*(12-2) ✓
- For q=(cos(x/2),sin(x/2),0,0), current m12 = sin(x), but test expects -sin(x) ✓

**Edit site**: `sympy/algebras/quaternion.py:532`
Change `m12 = 2*s*(q.c*q.d + q.b*q.a)` to `m12 = 2*s*(q.c*q.d - q.b*q.a)`

## Craft gate loop

### Iteration 1: Draft and apply

**Hypothesis**: Line 532 in `sympy/algebras/quaternion.py` has incorrect sign - change `m12 = 2*s*(q.c*q.d + q.b*q.a)` to `m12 = 2*s*(q.c*q.d - q.b*q.a)`

**Codex review**: Formula change is correct; matches standard `2*(yz - xw)` term. No functional issues detected.

**Applied diff**:
```diff
--- a/sympy/algebras/quaternion.py
+++ b/sympy/algebras/quaternion.py
@@ -529,7 +529,7 @@ class Quaternion(Expr):
 
         m10 = 2*s*(q.b*q.c + q.d*q.a)
         m11 = 1 - 2*s*(q.b**2 + q.d**2)
-        m12 = 2*s*(q.c*q.d + q.b*q.a)
+        m12 = 2*s*(q.c*q.d - q.b*q.a)
 
         m20 = 2*s*(q.b*q.d - q.c*q.a)
         m21 = 2*s*(q.c*q.d + q.b*q.a)
```

**Gate result**: ✅ PASS - All 5 tests passed including `test_quaternion_conversions`

**Trajectory**: Convergent (success) - FAIL_TO_PASS test now passes, no regressions.

## Audit: sympy__sympy-15349

### FAIL_TO_PASS
- test_quaternion_conversions: **PASS** ✓

### PASS_TO_PASS regressions
None

### Pre-existing (not counted, confirmed against base capture)
- test_quaternion_rotation_iss1593: Was FAIL on base, now PASS (bonus fix)

### Verdict
All FAIL_TO_PASS tests now pass. Zero PASS_TO_PASS regressions. The patch correctly fixes the sign error in the rotation matrix formula at line 532 of `sympy/algebras/quaternion.py`. As a bonus, the fix also resolves the pre-existing failure in `test_quaternion_rotation_iss1593`.
