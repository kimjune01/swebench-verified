# Hypothesis graph: sympy__sympy-22914

## H₁: Missing _print_Min and _print_Max methods (ACTIVE)
**Timestamp:** 2026-05-23 (Initial diagnosis)
**Mode:** Deduction
**Confidence:** 99%

### Observation
Test `test_PythonCodePrinter` fails at lines 61-62 with AssertionError:
- Expected: `prntr.doprint(Min(x, y)) == "min(x, y)"`
- Actual: `'((x) if (x <= y) else (y))'`
- Expected: `prntr.doprint(Max(x, y)) == "max(x, y)"`
- Actual: `'((x) if (x >= y) else (y))'`

### Root Cause
The `PythonCodePrinter` class (sympy/printing/pycode.py:425) lacks `_print_Min` and `_print_Max` methods. Without these, Min/Max expressions fall back to default Piecewise conditional printing instead of mapping to Python's built-in `min()` and `max()` functions.

### Evidence
1. `sympy/printing/pycode.py:18-20` — `_known_functions = {'Abs': 'abs',}` shows Min/Max are not in the known functions dict
2. `sympy/printing/pycode.py:425-473` — PythonCodePrinter class has no `_print_Min` or `_print_Max` methods
3. Grep confirmed: `grep -n "Min\|Max" sympy/printing/pycode.py` returns no matches
4. Runtime test: `PythonCodePrinter().doprint(Min(x, y))` outputs piecewise conditional

### Edit Sites
**Primary (matches problem statement):**
- `sympy/printing/pycode.py:427-472` — Add `_print_Min(self, expr)` and `_print_Max(self, expr)` methods to PythonCodePrinter class

**Alternative:**
- `sympy/printing/pycode.py:18-20` — Add `'Min': 'min', 'Max': 'max'` to `_known_functions` dict

### Status
Ready for implementation. Recommend Option 1 (explicit methods) per problem statement.

## Gate Loop - Iteration 1

**Fix applied:** Added `_print_Min` and `_print_Max` methods to `PythonCodePrinter` class in `sympy/printing/pycode.py` after the `_print_Not` method (lines 435-443).

```python
def _print_Min(self, expr):
    args = ", ".join(self._print(arg) for arg in expr.args)
    return "min({})".format(args)

def _print_Max(self, expr):
    args = ", ".join(self._print(arg) for arg in expr.args)
    return "max({})".format(args)
```

**Gate result:** ✅ PASS
- test_PythonCodePrinter: ok
- All 19 tests passed, 2 skipped

**Trajectory:** Convergent (resolved) — FAIL_TO_PASS tests now pass on first attempt.

---

# Audit: sympy__sympy-22914

## Patch Summary
The craft patch added `_print_Min` and `_print_Max` methods to the PythonCodePrinter class in `sympy/printing/pycode.py`, formatting Min/Max expressions as `min(args)` and `max(args)` respectively.

## FAIL_TO_PASS
- test_PythonCodePrinter: **PASS** ✓

## PASS_TO_PASS regressions
None — all 16 PASS_TO_PASS tests passed.

## Pre-existing (not counted, confirmed against base capture)
None — the 2 skipped tests (test_issue_18770, test_issue_20762) were also skipped on base due to missing dependencies (numpy, antlr).

## Gate Result
All tests passed. The fix successfully resolves the issue without introducing any regressions.

VERDICT: RESOLVED
RE-ENTER: none
