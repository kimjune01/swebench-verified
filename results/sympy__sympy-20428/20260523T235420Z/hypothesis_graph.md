# Hypothesis Graph: sympy__sympy-20428

## Problem Statement
Poly created from complex expression that simplifies to zero has inconsistent behavior:
- Prints as `Poly(0, x, domain='EX')`
- `is_zero` returns `False`
- `as_expr().is_zero` returns `True`
- Internal representation is `DMP([EX(complex_expr)], EX, None)` instead of `DMP([], EX, None)`

## Hypothesis 1: Expression.__bool__ uses syntactic equality instead of semantic zero-check

**Status**: Active
**Reasoning mode**: Deduction
**Confidence**: 95%

### Observation
The failing test constructs a Poly from a complex algebraic expression that simplifies to zero. The Poly is created with representation `DMP([EX(complex_expr)], EX, None)` instead of the expected `DMP([], EX, None)` for a zero polynomial.

Testing shows:
```python
expr.is_zero  # True
expr != 0     # True (syntactic check)
bool(EX(expr))  # True (should be False)
```

### Root Cause
`Expression.__bool__` at line 122 in `sympy/polys/domains/expressiondomain.py` uses:
```python
def __bool__(f):
    return f.ex != 0
```

The `!=` operator performs syntactic equality, not semantic evaluation. Complex expressions that simplify to zero but are not syntactically equal to 0 return `True` from this check.

When `dup_strip` (line 252 in `sympy/polys/densebasic.py`) tries to remove leading zeros:
```python
for cf in f:
    if cf:  # Calls __bool__ on EX coefficients
        break
```

The truthiness check fails for EX-wrapped expressions that are semantically zero but syntactically non-zero.

### Edit Sites
- `sympy/polys/domains/expressiondomain.py` line 122-123: Change `__bool__` to use `.is_zero` instead of `!= 0`
  - Current: `return f.ex != 0`
  - Proposed: `return f.ex.is_zero is not True`
  - Rationale: `.is_zero` returns `True` for zero, `False` for non-zero, `None` for unknown. Using `is not True` handles all three cases correctly.

### Supporting Evidence
- `sympy/polys/densebasic.py:252-267` - `dup_strip` uses truthiness check `if cf:` to detect zeros
- `sympy/polys/densebasic.py:917-948` - `dup_from_dict` calls `dup_strip` to clean up polynomial representation
- Test case confirms: `f.as_expr().is_zero` is `True` but `f.is_zero` is `False` due to unstripped `DMP([EX(0)], EX, None)`

### Call Path
1. `Poly(complex_zero_expr, x)` → `__new__` → `_from_expr`
2. `_from_expr` → `_dict_from_expr` → creates `{(0,): complex_zero_expr}`
3. `_from_dict` → `DMP.from_dict` → `dmp_from_dict` → `dup_from_dict`
4. `dup_from_dict` → `dup_strip` to remove leading zeros
5. `dup_strip` checks `if cf:` which calls `__bool__` on EX coefficient
6. `__bool__` returns `True` because `complex_zero_expr != 0` is `True`
7. Leading zero not stripped, resulting in `DMP([EX(...)], EX, None)`

## Gate Loop — craft

### Iteration 1: Initial fix applied

**Diff applied:**
```diff
--- a/sympy/polys/domains/expressiondomain.py
+++ b/sympy/polys/domains/expressiondomain.py
@@ -120,7 +120,7 @@ class ExpressionDomain(Domain):
             return not f == g
 
         def __bool__(f):
-            return f.ex != 0
+            return f.ex.is_zero is not True
 
         def gcd(f, g):
             from sympy.polys import gcd
```

**Codex pre-gate review:** No blocker. The change correctly implements semantic zero-checking instead of syntactic equality. Noted that `is_zero == None` remains truthy (conservative behavior), and truthiness is now decoupled from `__ne__(0)`.

**Gate result:** ✅ GREEN — all 156 tests passed including `test_issue_20427`

**Trajectory:** Convergent success — first attempt resolved the issue.

**Resolution:** The root cause diagnosis was correct. Changing `Expression.__bool__` from syntactic (`f.ex != 0`) to semantic (`f.ex.is_zero is not True`) allows `dup_strip` to properly identify and remove zero coefficients that simplify to zero, enabling the Poly to normalize to `DMP([], EX, None)` as expected.

## Audit: sympy__sympy-20428

### Patch Verification
**Patch content:**
```diff
--- a/sympy/polys/domains/expressiondomain.py
+++ b/sympy/polys/domains/expressiondomain.py
@@ -120,7 +120,7 @@ def __ne__(f, g):
             return not f == g
 
         def __bool__(f):
-            return f.ex != 0
+            return f.ex.is_zero is not True
```

### FAIL_TO_PASS
- `test_issue_20427`: **PASS** ✓

### PASS_TO_PASS regressions
None. All 156 tests passed with no failures.

### Pre-existing failures
None detected in gate run.

### Baseline Comparison
**On base (unpatched):**
- `test_issue_20427`: FAIL (AssertionError: `f == Poly(0, x, domain='EX')`)
- Total: 155 passed, 1 failed

**With patch:**
- `test_issue_20427`: PASS
- Total: 156 passed, 0 failed

### Verdict Analysis
✅ All FAIL_TO_PASS tests now pass (1/1)
✅ Zero PASS_TO_PASS regressions (0 failures)
✅ Fix correctly addresses root cause

The patch successfully resolves the issue by changing `Expression.__bool__` to use semantic zero-checking (`.is_zero is not True`) instead of syntactic equality (`!= 0`). This allows `dup_strip` to properly identify and remove coefficients that are semantically zero, normalizing the polynomial representation.

VERDICT: RESOLVED
RE-ENTER: none
