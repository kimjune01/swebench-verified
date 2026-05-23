# Hypothesis graph: sympy__sympy-14711

## H₀ (abduction → deduction): Vector addition fails with integer 0
**Status**: Active hypothesis  
**Reasoning mode**: Abduction → Deduction (traced code confirms)  
**Confidence**: 95% (deduction)

The test `assert A.x + 0 == A.x` fails because `Vector.__add__` unconditionally calls `_check_vector(other)` before checking if `other == 0`. When Python evaluates `A.x + 0`, it calls `A.x.__add__(0)`, which immediately raises `TypeError: A Vector must be supplied` at line 725 of vector.py.

### Evidence
- **Test failure**: `sympy/physics/vector/tests/test_vector.py:16` - `assert A.x + 0 == A.x`
- **Error location**: `sympy/physics/vector/vector.py:60` - `__add__` calls `_check_vector(other)` unconditionally
- **TypeError source**: `sympy/physics/vector/vector.py:725` - `_check_vector` raises TypeError for non-Vector types
- **Existing pattern**: `sympy/physics/vector/vector.py:124-125` - `__eq__` already handles this correctly:
  ```python
  if other == 0:
      other = Vector(0)
  ```
- **Zero vector support**: `sympy/physics/vector/vector.py:39-40` - `Vector(0)` creates zero vector with empty args

### Root Cause
The `__add__` method (lines 58-61) lacks a zero-check before type validation. The `__eq__` method demonstrates the correct pattern, but `__add__` doesn't follow it.

### Edit Sites
1. **Primary**: `sympy/physics/vector/vector.py` lines 58-61 - `Vector.__add__` method
   - Add check: `if other == 0: other = Vector(0)` before line 60
   - Place between line 59 (docstring) and line 60 (_check_vector call)

### Related Code
- `__radd__` (line 452): aliased to `__add__`, so fixing `__add__` fixes both
- `__rsub__` (line 318): calls `+ other`, will work once `__add__` is fixed
- No changes needed to `__sub__`, `__mul__`, or other operators

## Gate Loop - Iteration 1

**Fix Applied:**
Added zero-check to `Vector.__add__` method following the pattern already established in `Vector.__eq__`:
```python
def __add__(self, other):
    """The add operator for Vector. """
    if other == 0:
        other = Vector(0)
    other = _check_vector(other)
    return Vector(self.args + other.args)
```

**Codex Review:**
- Confirmed patch follows existing `__eq__` pattern
- Noted that `__radd__` is aliased to `__add__`, so both `A.x + 0` and `0 + A.x` work
- Suggested optimization (return self instead of Vector(0)) but not necessary for correctness

**Gate Result:**
✅ PASS - All tests passed including `test_Vector`
```
sympy/physics/vector/tests/test_vector.py[4] 
test_Vector ok
test_Vector_diffs ok
test_vector_var_in_dcm ok
test_vector_simplify ok
```

**Status:** RESOLVED - FAIL_TO_PASS test passes, no regressions detected

---

## Audit: sympy__sympy-14711

### Patch Applied
```diff
diff --git a/sympy/physics/vector/vector.py b/sympy/physics/vector/vector.py
index a048ee57f..5d89e0f91 100644
--- a/sympy/physics/vector/vector.py
+++ b/sympy/physics/vector/vector.py
@@ -57,6 +57,8 @@ def __hash__(self):
 
     def __add__(self, other):
         """The add operator for Vector. """
+        if other == 0:
+            other = Vector(0)
         other = _check_vector(other)
         return Vector(self.args + other.args)
```

### FAIL_TO_PASS Results
- **test_Vector**: PASS ✓ (was failing with `TypeError: A Vector must be supplied`, now passes)

### PASS_TO_PASS Results
- **test_Vector_diffs**: PASS ✓ (remained passing, no regression)
- **test_vector_var_in_dcm**: PASS ✓ (remained passing, no regression)

### PASS_TO_PASS Regressions
None.

### Pre-existing Failures (not counted)
None. All tests in the fail-on-base capture that were failing (test_Vector) now pass.

### Gate Output
```
sympy/physics/vector/tests/test_vector.py[4] 
test_Vector ok
test_Vector_diffs ok
test_vector_var_in_dcm ok
test_vector_simplify ok                                                     [OK]

================== tests finished: 4 passed, in 1.56 seconds ===================
```

### Analysis
The fix successfully addresses the root cause identified in H₀:
1. The `__add__` method now converts `0` to `Vector(0)` before type checking
2. This matches the existing pattern in `__eq__` and other operators
3. The fix is minimal and surgical - only 2 lines added
4. No regressions introduced in PASS_TO_PASS tests
5. All FAIL_TO_PASS tests now pass

VERDICT: RESOLVED
RE-ENTER: none
