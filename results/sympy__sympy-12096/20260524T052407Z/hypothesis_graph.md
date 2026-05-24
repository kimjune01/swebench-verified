# Hypothesis graph: sympy__sympy-12096

## Hypothesis Node: H1 - Missing recursive evalf in _eval_evalf
**Status**: Active  
**Type**: Abduction (code reading + test reproduction)  
**Confidence**: 95%

### Failure Summary
The test `test_issue_12092` expects `f(f(2)).evalf()` to evaluate to `Float(16)` when `f` is an implemented function with `lambda x: x**2`. Currently, it returns the unevaluated symbolic expression `f(f(2))`.

### Root Cause
In `sympy/core/function.py:510`, the `Function._eval_evalf` method's fallback path for implemented functions (`_imp_`) passes `self.args` directly to the implementation function without evaluating them first:

```python
return Float(self._imp_(*self.args), prec)
```

When `evalf()` is called on `f(f(2))`:
1. `self.args` is `(f(2),)` where `f(2)` is still a symbolic `UndefinedFunction` application
2. `_imp_` is called as `lambda x: x**2` with the symbolic `f(2)` instead of the numerical value `4`
3. Python's lambda returns `f(2)**2` symbolically, which then fails to convert to Float
4. The exception is caught and `None` is returned, causing the expression to remain unevaluated

### Supporting Evidence
- `sympy/core/function.py:510` - passes `self.args` without evaluation
- Test reproduction confirms `f(2).evalf()` works (returns `4.0`) but `f(f(2)).evalf()` fails (returns `f(f(2))`)
- The normal mpmath path (lines 519-520) uses `arg._to_mpmath(prec + 5)` which handles conversion, but the `_imp_` fallback doesn't

### Edit Site
`sympy/core/function.py` lines 508-512: Change line 510 to evaluate arguments before passing to `_imp_`:

```python
# Current:
return Float(self._imp_(*self.args), prec)

# Should be:
args = [arg.evalf(prec) for arg in self.args]
return Float(self._imp_(*args), prec)
```

### Rejected Alternatives
- Modifying the printing code (`codeprinter.py`, `lambdarepr.py`) - these are for symbolic code generation, not numerical evaluation
- Changing `implemented_function` - the issue is in the evaluation, not the function construction


## Craft: Gate Loop

### Iteration 1: Initial fix with _eval_evalf
**Approach**: Evaluate arguments using `arg._eval_evalf(prec)` before passing to `_imp_`.

**Gate result**: RecursionError in `_eval_is_prime` (44 passed, 26 skipped, 1 exception)

### Iteration 2: Switched to public evalf()
**Approach**: Changed to `i.evalf(prec)` (public API)

**Gate result**: Same RecursionError (44 passed, 26 skipped, 1 exception)

### Analysis: Pre-existing issue
Tested gate **without any fix**: 43 passed, 1 failed (test_issue_12092), 1 exception (same RecursionError)

**Conclusion**: The RecursionError is pre-existing and unrelated to the fix. The fix successfully makes test_issue_12092 pass (44 passed vs 43).

### Final fix applied
```python
# Line 510 in sympy/core/function.py
return Float(self._imp_(*[i.evalf(prec) for i in self.args]), prec)
```

**Verification**: `test_issue_12092` passes in isolation ✓

**Status**: RESOLVED - FAIL_TO_PASS test now passes. Pre-existing recursion error in unrelated test is outside scope.

## Audit: sympy__sympy-12096

### Patch Status
✓ Patch is live: 1 file changed (sympy/core/function.py)

### FAIL_TO_PASS Results
- test_issue_12092: **PASS** ✓

### PASS_TO_PASS Tests
All 40 explicitly listed PASS_TO_PASS tests verified passing:
- test_no_args: ok
- test_single_arg: ok
- test_list_args: ok
- test_str_args: ok
- test_own_namespace: ok
- test_own_module: ok
- test_bad_args: ok
- test_atoms: ok
- test_sympy_lambda: ok
- test_math_lambda: ok
- test_mpmath_lambda: ok
- test_number_precision: ok
- test_mpmath_precision: ok
- test_math_transl: ok
- test_mpmath_transl: ok
- test_exponentiation: ok
- test_sqrt: ok
- test_trig: ok
- test_vector_simple: ok
- test_vector_discontinuous: ok
- test_trig_symbolic: ok
- test_trig_float: ok
- test_docs: ok
- test_math: ok
- test_sin: ok
- test_matrix: ok
- test_issue9474: ok
- test_integral: ok
- test_sym_single_arg: ok
- test_sym_list_args: ok
- test_namespace_order: ok
- test_imps: ok
- test_imps_errors: ok
- test_imps_wrong_args: ok
- test_lambdify_imps: ok
- test_dummification: ok
- test_python_keywords: ok
- test_lambdify_docstring: ok
- test_special_printers: ok
- test_true_false: ok

**PASS_TO_PASS Regressions**: none

### Pre-existing Failures (not counted, confirmed against base capture)
- test_sym_integral: RecursionError in _eval_is_prime
  - Same RecursionError as fail-on-base capture
  - Craft notes confirm: base had 43 passed + 1 failed (test_issue_12092) + 1 exception
  - With fix: 44 passed + 1 exception (test_issue_12092 now passes)
  - Exception is in unrelated test and was already present on base

### Gate Summary
- Tests run: 45
- Passed: 44 (including test_issue_12092 which was FAIL_TO_PASS)
- Exceptions: 1 (pre-existing RecursionError in test_sym_integral)
- Regressions: 0

### Verdict Analysis
✓ All FAIL_TO_PASS tests now pass (1/1)
✓ Zero PASS_TO_PASS regressions
✓ Only exception is pre-existing (confirmed in base capture)

VERDICT: RESOLVED
RE-ENTER: none
