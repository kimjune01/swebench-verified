# Hypothesis graph: sympy__sympy-21612

## H₀: Missing parentheses for Pow base in denominator (abduction, 85%)

**Observation:** The test `assert str(Mul(x, Pow(1/y, -1, evaluate=False), evaluate=False)) == 'x/(1/y)'` fails with output `'x/1/y'` instead of expected `'x/(1/y)'`.

**Root cause:** In `sympy/printing/str.py`, the `_print_Mul` method at lines 335-336 only checks if `item.base` is a `Mul` when deciding whether to add parentheses in the denominator. It doesn't check if `item.base` is a `Pow` with negative exponent (representing a division like `1/y`).

When `Mul(x, Pow(1/y, -1, evaluate=False), evaluate=False)` is printed:
1. The code recognizes `Pow(1/y, -1)` has negative exponent
2. Since exp is exactly -1, it appends `item.base` (which is `1/y`) to the denominator list `b`
3. The check `isinstance(item.base, Mul)` fails because `1/y` is `Pow(y, -1)`, not a Mul
4. So it's not added to `pow_paren` and doesn't get parenthesized
5. Result: `x/1/y` instead of `x/(1/y)`

**Supporting evidence:**
- `sympy/printing/str.py:335-336` — condition only checks for Mul:
  ```python
  if (len(item.args[0].args) != 1 and
          isinstance(item.base, Mul)):
  ```
- `sympy/printing/str.py:337-338` — comment references issue 14160, which was for Mul in denominator

**Edit sites:**
- `sympy/printing/str.py` lines 335-336: Extend condition to also check if `item.base` is a Pow with negative exponent using `isinstance(item.base, Pow) and bool(item.base.exp.as_coeff_Mul()[0] < 0)`

**Confidence:** Abduction — 85% (hypothesis derived from code inspection and test case analysis, but not yet tested)

## Gate Loop - Iteration 1

**Drafted fix:** Extended the isinstance check at line 336 from `isinstance(item.base, Mul)` to `isinstance(item.base, (Mul, Pow))`.

**codex feedback:** Initial draft used complex condition `isinstance(item.base, Pow) and bool(item.base.exp.as_coeff_Mul()[0] < 0)` which was too broad. codex suggested simpler fix: just add `Pow` to the isinstance tuple check.

**Applied diff:**
```diff
--- a/sympy/printing/str.py
+++ b/sympy/printing/str.py
@@ -333,7 +333,7 @@ def apow(i):
                     b.append(apow(item))
                 else:
                     if (len(item.args[0].args) != 1 and
-                            isinstance(item.base, Mul)):
+                            isinstance(item.base, (Mul, Pow))):
                         # To avoid situations like #14160
                         pow_paren.append(item)
                     b.append(item.base)
```

**Gate result:** PASS - all 100 tests passed including test_Mul

**Trajectory:** Convergent (green) - FAIL_TO_PASS test now passes

---

# Audit: sympy__sympy-21612

## FAIL_TO_PASS
- test_Mul: **PASS** ✓

## PASS_TO_PASS regressions
none

## Pre-existing (not counted, confirmed against base capture)
none

## Summary
The fix successfully resolved the issue. The change from `isinstance(item.base, Mul)` to `isinstance(item.base, (Mul, Pow))` at line 336 in `sympy/printing/str.py` correctly handles the case where a Pow expression with negative exponent appears in the denominator, ensuring it gets parenthesized properly.

**Gate output:** 100 tests passed, 0 failed
- FAIL_TO_PASS test (test_Mul): now PASS
- All PASS_TO_PASS tests: remain PASS
- Regressions: 0

VERDICT: RESOLVED
RE-ENTER: none
