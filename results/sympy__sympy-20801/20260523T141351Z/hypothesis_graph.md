# Hypothesis graph: sympy__sympy-20801

## H₀: Float.__eq__ zero-check happens before Boolean-check (abduction)

**Date**: 2026-05-23
**Mode**: abduction (60-85% confidence)

**Observation**: `S(0.0) == S.false` returns `True` but should return `False`. All other combinations return `False` correctly:
- `S.false == S(0.0)` → `False` (correct)
- `S(0) == S.false` → `False` (correct)
- `S.false == S(0)` → `False` (correct)

**Root cause**: In `Float.__eq__` (line 1383 in `sympy/core/numbers.py`), the zero-check happens BEFORE the Boolean-check:

```python
def __eq__(self, other):
    from sympy.logic.boolalg import Boolean
    try:
        other = _sympify(other)
    except SympifyError:
        return NotImplemented
    if not self:  # Line 1389 - checks if self is zero FIRST
        return not other  # Line 1390 - returns Python bool of 'not other'
    if isinstance(other, Boolean):  # Line 1391 - checks Boolean SECOND
        return False  # Line 1392
    ...
```

When `S(0.0) == S.false`:
1. `self = S(0.0)`, `other = S.false`
2. Line 1389: `if not self` evaluates to `True` (0.0 is falsy in Python)
3. Line 1390: `return not other` → `return not S.false` → returns `True` (because `not S.false` is `True` in Python)
4. Line 1391 (Boolean check) is never reached

**Why Integer/Rational don't have this bug**: Commit dcfcf9d72b ("handle Int/BooleanAtom comparison") added a Number-type check to `Rational.__eq__` that returns `False` before the zero-check for non-Numbers:

```python
if not isinstance(other, Number):
    # S(0) == S.false is False
    # S(0) == False is True
    return False
```

Since `S.false` is not a Number, this returns `False` immediately. But Float.__eq__ doesn't have this check - it has a Boolean check instead, but it's ordered AFTER the zero-check.

**Confidence**: Abduction 75% - I traced the code path and can quote the exact lines, but haven't verified the fix empirically.

**Edit site**: `sympy/core/numbers.py` lines 1389-1392: Move the Boolean check (lines 1391-1392) to BEFORE the zero check (lines 1389-1390).

## craft gate-loop iteration 1

**Drafted fix**: Moved `isinstance(other, Boolean)` check before `if not self:` and guarded zero-shortcut with `other.is_Number`.

**codex review 1**: Warned that simple reordering is too narrow — zero Float can compare equal to any falsy sympified object, not just Boolean. Suggested guarding the zero-shortcut with `other.is_Number and not other`.

**Applied diff**:
```diff
--- a/sympy/core/numbers.py
+++ b/sympy/core/numbers.py
@@ -1386,10 +1386,10 @@ class Float(Number):
             other = _sympify(other)
         except SympifyError:
             return NotImplemented
+        if isinstance(other, Boolean):
+            return False
         if not self:
-            return not other
+            return other.is_Number and not other
-        if isinstance(other, Boolean):
-            return False
         if other.is_NumberSymbol:
```

**Gate result**: ✅ PASS — `test_zero_not_false` passes, 98 tests passed total.

**Resolution**: Fix successful. The Boolean check now executes before the zero-check, and the zero-shortcut is guarded to only apply to Number types, preventing false equality with Boolean and other non-numeric sympified objects.

## Audit: sympy__sympy-20801

**Date**: 2026-05-23

### FAIL_TO_PASS
- `test_zero_not_false`: **PASS** ✓

### PASS_TO_PASS regressions
None — all 98 PASS_TO_PASS tests still passing.

### Pre-existing (not counted, confirmed against base capture)
- `test_mpmath_issues`: expected to fail (f) on both base and patched
- `test_numpy_to_float`: skipped (s) — numpy not installed

### Verdict
All FAIL_TO_PASS tests pass. Zero regressions. The fix successfully resolved the issue where `S(0.0) == S.false` incorrectly returned `True` by:
1. Moving the Boolean type check before the zero-check
2. Guarding the zero-shortcut to only apply to Number types

**VERDICT**: RESOLVED
**RE-ENTER**: none
