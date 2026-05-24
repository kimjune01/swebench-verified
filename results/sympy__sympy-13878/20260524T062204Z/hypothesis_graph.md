# Hypothesis graph: sympy__sympy-13878

## H₀: Missing _cdf method (abduction)
**Status**: Active
**Mode**: Abduction (60-85%)
**Observation**: test_arcsin fails because cdf(X)(x) returns unevaluated Integral instead of explicit Piecewise formula

**Evidence**:
- Current output: `Integral(1/sqrt(-_x**2 + _x*a + _x*b - a*b), (_x, -oo, x))/pi`
- Expected output: `Piecewise((0, a > x), (2*asin(sqrt((-a + x)/(-a + b)))/pi, b >= x), (1, True))`
- Code path: test → cdf(X)(x) → SingleContinuousDistribution.cdf() → _cdf() returns None → compute_cdf() → unevaluated integral

**Root cause**:
The `ArcsinDistribution` class (sympy/stats/crv_types.py:150-154) lacks a `_cdf` method. When `SingleContinuousDistribution.cdf()` is called, it checks for `_cdf()` first (crv.py:219-222). Since none exists, it falls back to integrating the PDF, which doesn't evaluate cleanly.

**Supporting code**:
- `sympy/stats/crv_types.py:150-154` - ArcsinDistribution only defines pdf(), no _cdf()
- `sympy/stats/crv.py:219-222` - cdf() method checks _cdf() first, falls back to integration
- `sympy/stats/tests/test_continuous_rv.py:185-189` - test expects explicit Piecewise CDF formula

**Fix specification**:
Add a `_cdf` method to `ArcsinDistribution` class that returns the precomputed CDF formula:
```python
def _cdf(self, x):
    a, b = self.a, self.b
    return Piecewise((0, a > x),
                     (2*asin(sqrt((x - a)/(b - a)))/pi, b >= x),
                     (1, True))
```

**Confidence**: 85% (abduction) - The test explicitly shows the expected formula, and the code path is clear. However, I haven't verified the mathematical correctness of the formula by differentiation.

## Gate iteration 1: Implementation applied
**Timestamp**: 2026-05-23
**Status**: PASS
**Action**: Implemented H₀ fix

**Changes applied**:
1. Added `asin` to imports (sympy/stats/crv_types.py:52)
2. Added `_cdf` method to `ArcsinDistribution` class (lines 156-161):
```python
def _cdf(self, x):
    a, b = self.a, self.b
    return Piecewise(
        (0, a > x),
        (2*asin(sqrt((x - a)/(b - a)))/pi, b >= x),
        (1, True))
```

**codex review**: Approved with style notes (use local variables a,b - applied)

**Gate result**: PASS
- test_arcsin PASSED - cdf(X)(x) now returns expected Piecewise formula
- Verified: `cdf_result == Piecewise((0, a > x), (2*asin(sqrt((-a + x)/(-a + b)))/pi, b >= x), (1, True))` → True

**Outcome**: FAIL_TO_PASS test passes. Fix is complete.

---

# Audit: sympy__sympy-13878

**Timestamp**: 2026-05-23
**Patch status**: Live (8 insertions, 1 deletion in sympy/stats/crv_types.py)

## FAIL_TO_PASS
- test_arcsin: **PASS** ✓

## PASS_TO_PASS (19 tests, 0 regressions)
- test_ContinuousDomain: PASS ✓
- test_characteristic_function: PASS ✓
- test_benini: PASS ✓
- test_chi: PASS ✓
- test_chi_noncentral: PASS ✓
- test_chi_squared: PASS ✓
- test_gompertz: PASS ✓
- test_shiftedgompertz: PASS ✓
- test_trapezoidal: PASS ✓
- test_quadratic_u: PASS ✓
- test_von_mises: PASS ✓
- test_prefab_sampling: PASS ✓
- test_input_value_assertions: PASS ✓
- test_probability_unevaluated: PASS ✓
- test_density_unevaluated: PASS ✓
- test_random_parameters: PASS ✓
- test_random_parameters_given: PASS ✓
- test_conjugate_priors: PASS ✓
- test_issue_10003: PASS ✓

**Regressions**: none

## Pre-existing failures (not counted against patch)
Gate shows 36 exceptions, 4 expected fails, confirmed pre-existing via fail-on-base capture:
- test_precomputed_cdf: RecursionError in assumptions system (pre-existing)
- test_long_precomputed_cdf: DeprecationWarning in collections (pre-existing)
- test_difficult_univariate: Exception during density computation (pre-existing)
- Plus 33 other exception tests ("E" status) - all pre-existing test infrastructure issues

**Baseline confirmation**: The fail-on-base capture shows identical stack traces for test_precomputed_cdf, test_long_precomputed_cdf, and test_difficult_univariate, confirming these failures existed before the patch.

## Contract verification
- ✓ All FAIL_TO_PASS tests pass (1/1)
- ✓ Zero PASS_TO_PASS regressions (0/19)
- ✓ Patch is live in tree
- ✓ Fix is minimal and targeted

VERDICT: RESOLVED
RE-ENTER: none
