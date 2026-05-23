# Hypothesis graph: sympy__sympy-14976

## Hypothesis H₀ (Phase 1 - Baseline)
**Type:** Abduction  
**Status:** Active  

The tests fail because MpmathPrinter doesn't wrap Rational numerators and denominators with mpmath.mpf(), resulting in Python's limited-precision float division instead of mpmath's arbitrary-precision division.

**Evidence:**
- `test_MpmathPrinter` expects: `'mpmath.mpf(1)/mpmath.mpf(2)'`
- `test_MpmathPrinter` gets: `'1/2'`
- `test_nsolve_rational` expects 100-digit precision but gets ~17-digit float precision

## Phase 2 - Localization

**Call path:**
1. `test_MpmathPrinter` → `MpmathPrinter.doprint(Rational(1, 2))`
2. No `_print_Rational` method in MpmathPrinter
3. Falls back to inherited `StrPrinter._print_Rational` (sympy/printing/str.py:594)
4. Returns plain `"1/2"` string

**Suspect set:**
- `sympy/printing/pycode.py` lines 314-354: MpmathPrinter class definition
- Missing `_print_Rational` method

**Inheritance chain:**
- MpmathPrinter → PythonCodePrinter → CodePrinter → StrPrinter
- StrPrinter._print_Rational outputs "p/q" format without type wrapping

## Phase 3 - Root Cause

**Root cause:** MpmathPrinter lacks a `_print_Rational` method to wrap rational numbers with mpmath.mpf() for arbitrary precision.

**Confidence:** Deduction — 98%

**Supporting evidence:**
1. `sympy/printing/pycode.py:314-354` — MpmathPrinter class has `_print_Float` method (wraps floats in mpmath.mpf) but no `_print_Rational` method
2. `sympy/printing/pycode.py:325-333` — The `_print_Float` method shows the pattern: wraps values with `self._module_format('mpmath.mpf')`
3. `sympy/printing/str.py:594-601` — StrPrinter._print_Rational returns `"%s/%s" % (expr.p, expr.q)` — plain division
4. Other code printers override _print_Rational for their target environment:
   - `sympy/printing/rcode.py:158` — RCodePrinter wraps with `.0` for float division
   - `sympy/printing/ccode.py:301` — CCodePrinter wraps with `.0` and suffix for float division

**What needs to change:**
Add a `_print_Rational` method to MpmathPrinter that wraps both numerator and denominator with `mpmath.mpf()`, following the same pattern as `_print_Float`.

## Phase 4 - Edit Sites

**Primary edit site:**
- `sympy/printing/pycode.py` lines 325-354 (inside MpmathPrinter class)
  - Add new method `_print_Rational` after the `_print_Float` method (after line 333)
  - Implementation: `return '{0}({1})/{0}({2})'.format(self._module_format('mpmath.mpf'), expr.p, expr.q)`
  - This wraps both numerator and denominator in mpmath.mpf() to maintain arbitrary precision

**No other edit sites required** — verified via grep that:
- No other files call MpmathPrinter._print_Rational
- No subclasses of MpmathPrinter exist that would need updates
- The change is isolated to the printer class itself

## Verification strategy

After implementing the fix:
1. Run `test_MpmathPrinter` — should pass with output `'mpmath.mpf(1)/mpmath.mpf(2)'`
2. Run `test_nsolve_rational` — should pass with full 100-digit precision
3. Verify lambdify with mpmath generates correct code for rationals


---

## Craft gate-loop

### Iteration 1: Initial implementation

**Action**: Added `_print_Rational` method to MpmathPrinter class following codex's refined suggestion to handle `e.q == 1` case separately.

**Implementation**:
```python
def _print_Rational(self, e):
    if e.q == 1:
        return self._print(e.p)
    return "{0}({1})/{0}({2})".format(
        self._module_format("mpmath.mpf"), e.p, e.q)
```

**Gate result**: PASS ✓
- test_MpmathPrinter: OK
- test_nsolve_rational: OK
- All 16 tests passed, 2 expected to fail

**Trajectory**: Convergent (success) - FAIL_TO_PASS tests now pass, no regressions.

---

# Audit: sympy__sympy-14976

## FAIL_TO_PASS
- test_MpmathPrinter: PASS ✅

## PASS_TO_PASS (all 13 tests)
- test_PythonCodePrinter: PASS ✅
- test_NumPyPrinter: PASS ✅
- test_SciPyPrinter: PASS ✅
- test_pycode_reserved_words: PASS ✅
- test_printmethod: PASS ✅
- test_codegen_ast_nodes: PASS ✅
- test_nsolve_denominator: PASS ✅
- test_nsolve: PASS ✅
- test_issue_6408: PASS ✅
- test_increased_dps: PASS ✅
- test_nsolve_precision: PASS ✅
- test_nsolve_complex: PASS ✅
- test_nsolve_dict_kwarg: PASS ✅

## PASS_TO_PASS regressions
none

## Pre-existing (not counted, confirmed against base capture)
- test_nsolve_rational (was failing on base, now PASSES as bonus)

## Summary
The craft patch successfully adds a `_print_Rational` method to MpmathPrinter that converts Rational numbers to the mpf format by printing numerator and denominator as mpf values and dividing them. This fixes the failing test_MpmathPrinter without introducing any regressions. As a bonus, it also fixes the pre-existing test_nsolve_rational failure.

Patch applied:
```python
def _print_Rational(self, e):
    if e.q == 1:
        return self._print(e.p)
    return "{0}({1})/{0}({2})".format(
        self._module_format("mpmath.mpf"), e.p, e.q)
```

VERDICT: RESOLVED
RE-ENTER: none
