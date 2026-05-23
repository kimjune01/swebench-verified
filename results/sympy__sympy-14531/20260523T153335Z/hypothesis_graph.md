# Hypothesis graph: sympy__sympy-14531

## Hypothesis Node: Initial Diagnosis

**Type**: Abduction  
**Confidence**: 95% (deduction - traced through code)

### Failure Summary
- `test_python_relational` fails: `python(Eq(x, y))` returns `'e = Eq(x, y)'` instead of `"x = Symbol('x')\ny = Symbol('y')\ne = Eq(x, y)"`
- `test_Rational` fails: `sstr(Eq(x, Rational(2, 3)), sympy_integers=True)` returns `'Eq(x, 2/3)'` instead of `'Eq(x, S(2)/3)'`

### Root Cause
The `_print_Relational` method in `sympy/printing/str.py` (line 632) and `_print_Limit` method (lines 219-221) directly format subexpressions using Python's `%` string formatting operator, which calls `str()` on the arguments instead of going through the printer's `self._print()` method.

This causes two issues:
1. Printer settings (like `sympy_integers=True`) are not propagated to subexpressions
2. For `PythonPrinter`, symbols within the expression are not collected into `self.symbols` because `_print_Symbol()` is never called

### Supporting Evidence

**File**: `sympy/printing/str.py:632`
```python
return '%s(%s, %s)' % (charmap[expr.rel_op], expr.lhs, expr.rhs)
```
This directly formats `expr.lhs` and `expr.rhs` without calling `self._print()`.

**File**: `sympy/printing/str.py:219-221`
```python
if str(dir) == "+":
    return "Limit(%s, %s, %s)" % (e, z, z0)
else:
    return "Limit(%s, %s, %s, dir='%s')" % (e, z, z0, dir)
```
This directly formats `e`, `z`, `z0` without calling `self._print()`.

**Comparison with correct implementation** - `sympy/printing/str.py:199` (_print_AccumBounds):
```python
return "AccumBounds(%s, %s)" % (self._print(i.min), self._print(i.max))
```
This correctly uses `self._print()` on subexpressions.

### Edit Sites

1. **sympy/printing/str.py:632** - Change:
   ```python
   return '%s(%s, %s)' % (charmap[expr.rel_op], expr.lhs, expr.rhs)
   ```
   To:
   ```python
   return '%s(%s, %s)' % (charmap[expr.rel_op], self._print(expr.lhs), self._print(expr.rhs))
   ```

2. **sympy/printing/str.py:219** - Change:
   ```python
   return "Limit(%s, %s, %s)" % (e, z, z0)
   ```
   To:
   ```python
   return "Limit(%s, %s, %s)" % (self._print(e), self._print(z), self._print(z0))
   ```

3. **sympy/printing/str.py:221** - Change:
   ```python
   return "Limit(%s, %s, %s, dir='%s')" % (e, z, z0, dir)
   ```
   To:
   ```python
   return "Limit(%s, %s, %s, dir='%s')" % (self._print(e), self._print(z), self._print(z0), dir)
   ```


## Gate Loop 1 - RESOLVED

**Iteration 1:**

**Hypothesis:** `_print_Relational` and `_print_Limit` methods bypass `self._print()`, preventing settings propagation and symbol tracking.

**Fix applied:**
- `sympy/printing/str.py:219` - Changed `_print_Limit` to call `self._print(e)`, `self._print(z)`, `self._print(z0)` for both branches (dir=="+" and dir!="+" cases)
- `sympy/printing/str.py:632` - Changed `_print_Relational` to call `self._print(expr.lhs)` and `self._print(expr.rhs)`

**Codex pre-gate review:** "No blocker in the proposed diff. It fixes the stated root cause... patch is directionally correct and likely sufficient for the failing tests."

**Gate result:** ✅ PASS
- test_python_relational: ok
- test_Rational: ok  
- All 88 tests passed, 1 expected to fail

**Trajectory:** Convergent (first attempt success)

**Status:** RESOLVED - Both FAIL_TO_PASS tests now pass. The fix correctly routes subexpressions through the printer's `self._print()` method, enabling settings like `sympy_integers=True` to propagate and symbol tracking to work properly in PythonPrinter.

## Audit: sympy__sympy-14531

### Phase 1: Patch Verification
```
sympy/printing/str.py | 6 +++---
1 file changed, 3 insertions(+), 3 deletions(-)
```
Patch is live in the container.

### Phase 2: Gate Execution
Full test suite executed successfully. 88 tests passed, 1 expected to fail.

### Phase 3: Result Classification

#### FAIL_TO_PASS (must now PASS):
- `test_python_relational`: **PASS** ✓
- `test_Rational`: **PASS** ✓

#### PASS_TO_PASS regressions:
**None** - All 86 PASS_TO_PASS tests remain passing.

#### Pre-existing (not counted, confirmed against base capture):
- `test_python_functions_conjugates`: expected fail ('f') on both base and patched version

### Phase 4: Analysis

The patch successfully fixes both failing tests by ensuring that `_print_Relational` and `_print_Limit` methods route subexpressions through `self._print()` instead of direct string formatting. This enables:

1. Settings propagation (e.g., `sympy_integers=True`) to nested expressions
2. Symbol tracking in `PythonPrinter` via proper `_print_Symbol()` calls

**Changed lines:**
- Line 219: `return "Limit(%s, %s, %s)" % (self._print(e), self._print(z), self._print(z0))`
- Line 221: `return "Limit(%s, %s, %s, dir='%s')" % (self._print(e), self._print(z), self._print(z0), dir)`
- Line 633: `return '%s(%s, %s)' % (charmap[expr.rel_op], self._print(expr.lhs), self._print(expr.rhs))`

No test regressions. No unintended side effects. The fix is minimal, targeted, and complete.

