# Hypothesis graph: sympy__sympy-18763

## H₀: Missing parenthesization in _print_Subs (abduction)

**Observation**: The test `test_latex_subs` expects Subs expressions to have parentheses around the substituted expression, but they are missing in the actual output.

**Hypothesis**: The `_print_Subs` method at `sympy/printing/latex.py:699-707` directly prints the expression using `self._print(expr)` instead of using `self.parenthesize(expr, PRECEDENCE["Mul"])` like similar constructs (Integral, Derivative) do.

**Evidence**:
- `sympy/printing/latex.py:701`: `latex_expr = self._print(expr)` — no precedence-based parenthesization
- `sympy/printing/latex.py:695-697` (Derivative): uses `self.parenthesize(expr.expr, PRECEDENCE["Mul"], strict=True)`
- `sympy/printing/latex.py:738-740` (Integral): uses `self.parenthesize(expr.function, PRECEDENCE["Mul"], strict=True)`
- Test expectation: Both `x*y` (precedence 50) and `-x+y` (precedence 40) should be parenthesized, which requires `strict=False` (default) unlike Integral/Derivative which use `strict=True`

**Confidence**: deduction — 98%

**Edit site**: `sympy/printing/latex.py:701` — change to use `self.parenthesize(expr, PRECEDENCE["Mul"])`


---
## craft: gate iteration 1

**Change applied:**
```diff
--- a/sympy/printing/latex.py
+++ b/sympy/printing/latex.py
@@ -698,7 +698,7 @@ class LatexPrinter(Printer):
 
     def _print_Subs(self, subs):
         expr, old, new = subs.args
-        latex_expr = self._print(expr)
+        latex_expr = self.parenthesize(expr, PRECEDENCE["Mul"])
         latex_old = (self._print(e) for e in old)
         latex_new = (self._print(e) for e in new)
         latex_subs = r'\\ '.join(
```

**codex pre-gate review:** No blocking issue. `self.parenthesize(expr, PRECEDENCE["Mul"])` correctly parenthesizes both `Add` (precedence 40) and `Mul` (precedence 50) expressions.

**Gate result:** ✅ PASS
- `test_latex_subs` now passes
- 143 tests passed total
- 2 pre-existing exceptions (test_issue_8470, test_issue_13559 - parsing errors unrelated to this change)
- No new regressions

**Status:** RESOLVED - FAIL_TO_PASS test passes

---
## Audit: sympy__sympy-18763 (verification run)

### FAIL_TO_PASS
- test_latex_subs: **PASS** ✓ (was erroring with parse_expr issue on base, now passes)

### PASS_TO_PASS regressions
**None** — all 143 tests that passed on base still pass

### Pre-existing failures (not counted, confirmed against base capture)
- test_builtin_without_args_mismatched_names: expected fail (f) — same on base
- test_issue_8470: ERROR (ValueError: Name node can't be used with 'False' constant) — same on base
- test_issue_13559: ERROR (ValueError: Name node can't be used with 'False' constant) — same on base

### Analysis
The patch successfully fixes test_latex_subs by changing line 701 in sympy/printing/latex.py from:
```python
latex_expr = self._print(expr)
```
to:
```python
latex_expr = self.parenthesize(expr, PRECEDENCE["Mul"])
```

This ensures that expressions within Subs are properly parenthesized based on precedence, matching the behavior of Integral and Derivative printing. The fix is minimal, surgical, and introduces zero regressions.

All failures in the current gate run are pre-existing (confirmed by comparing against the fail-on-base capture) and unrelated to the LaTeX printing changes.

VERDICT: RESOLVED
RE-ENTER: none
