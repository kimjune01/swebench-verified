# Hypothesis Graph: sympy__sympy-22714

## H0 (abduction)
The test `test_issue_22684` fails because creating `Point(1, 2)` inside an `evaluate(False)` context raises `ValueError: Imaginary coordinates are not permitted.`

## H1 (deduction — 99%)
**Root cause:** Line 155 in `sympy/geometry/point.py` checks for imaginary coordinates with:
```python
if any(a.is_number and im(a) for a in coords):
    raise ValueError('Imaginary coordinates are not permitted.')
```

When `evaluate=False` is in effect (globally via `with evaluate(False)`), calling `im(1)` returns an unevaluated `im(1)` expression instead of `0`. This unevaluated expression is truthy, causing the check to incorrectly conclude that real coordinates have imaginary parts.

**Evidence:**
```python
# Without evaluate(False): im(1) = 0, bool(im(1)) = False
# With evaluate(False): im(1) = im(1), bool(im(1)) = True
```

**Fix:** Wrap the `im(a)` call in an `evaluate(True)` context to force evaluation of the imaginary part check, even when `evaluate=False` is in effect globally.


## Gate Loop — Craft

### Iteration 1

**Drafted fix:**
- Import `evaluate` as `evaluate_context` from `sympy.core.parameters` (aliased to avoid name collision with the `evaluate` parameter in Point constructor)
- Wrap the imaginary coordinate check (line 155) in `with evaluate_context(True):` to force evaluation of `im(a)` even when global `evaluate=False` is active

**codex volley 1:** Caught critical name collision - `evaluate` is a local variable in the constructor. Suggested using alias `evaluate_context`.

**codex volley 2:** Approved revised patch with alias.

**Applied changes:**
```diff
--- a/sympy/geometry/point.py
+++ b/sympy/geometry/point.py
@@ -24,7 +24,7 @@ from sympy.core import S, sympify, Expr
 from sympy.core.add import Add
 from sympy.core.containers import Tuple
 from sympy.core.numbers import Float
-from sympy.core.parameters import global_parameters
+from sympy.core.parameters import global_parameters, evaluate as evaluate_context
 from sympy.simplify import nsimplify, simplify
 from sympy.geometry.exceptions import GeometryError
 from sympy.functions.elementary.miscellaneous import sqrt
@@ -153,8 +153,9 @@ class Point(GeometryEntity):
                         on_morph value should be 'error',
                         'warn' or 'ignore'.'''))
         if any(coords[dim:]):
             raise ValueError('Nonzero coordinates cannot be removed.')
-        if any(a.is_number and im(a) for a in coords):
-            raise ValueError('Imaginary coordinates are not permitted.')
+        with evaluate_context(True):
+            if any(a.is_number and im(a) for a in coords):
+                raise ValueError('Imaginary coordinates are not permitted.')
         if not all(isinstance(a, Expr) for a in coords):
             raise TypeError('Coordinates must be valid SymPy expressions.')
```

**Gate result:** ✅ PASS - all 13 tests passed including `test_issue_22684`

**Resolution:** The recon diagnosis was correct. Wrapping the imaginary coordinate validation in `evaluate_context(True)` ensures `im(a)` evaluates to its numeric value (0 for real numbers) rather than remaining as an unevaluated expression, fixing the false positive when `Point(1, 2)` is created inside an `evaluate(False)` context.

---

## Audit

**Gate output:** All 13 tests passed.

### FAIL_TO_PASS
- test_issue_22684: ✅ PASS (was failing on base with `ValueError: Imaginary coordinates are not permitted.`)

### PASS_TO_PASS
All 11 tests passed:
- test_point: ok
- test_point3D: ok
- test_Point2D: ok
- test_issue_9214: ok
- test_issue_11617: ok
- test_transform: ok
- test_concyclic_doctest_bug: ok
- test_arguments: ok
- test_unit: ok
- test_dot: ok
- test__normalize_dimension: ok

### PASS_TO_PASS regressions
None.

### Pre-existing failures
None.

### Analysis
The fix successfully resolves test_issue_22684 by wrapping the imaginary coordinate check in `evaluate_context(True)`, which forces `im(a)` to evaluate to its numeric value even when `evaluate(False)` is active globally. No regressions introduced.

**VERDICT:** RESOLVED
**RE-ENTER:** none
