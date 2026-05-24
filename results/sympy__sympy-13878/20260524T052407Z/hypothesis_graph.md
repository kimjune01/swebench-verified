# Hypothesis graph: sympy__sympy-13878

## H₁: Missing _cdf method in ArcsinDistribution (abduction, 85%)

**Status**: Active  
**Mode**: Abduction  
**Confidence**: 85%

### Observation
The test `test_arcsin` fails with exceptions during CDF computation. When running `cdf(Arcsin('x', a, b))(x)`, the system attempts to compute the CDF by integrating the PDF, which leads to infinite recursion in the assumptions system.

### Hypothesis
The ArcsinDistribution class (lines 150-154 in `sympy/stats/crv_types.py`) lacks a `_cdf` method. The base class `SingleContinuousDistribution` has a `cdf` method (line 214 in `sympy/stats/crv.py`) that first checks for a `_cdf` method. If it exists, it uses that; otherwise, it falls back to `compute_cdf(**kwargs)(x)` which performs integration. For Arcsin, integration of the PDF does not work well.

### Evidence
- `sympy/stats/crv_types.py:150-154` — ArcsinDistribution only has `pdf` method, no `_cdf`
- `sympy/stats/crv.py:214-220` — Base class checks `_cdf(x)` first, falls back to `compute_cdf`
- `sympy/stats/tests/test_continuous_rv.py:188-190` — Test expects: `Piecewise((0, a > x), (2*asin(sqrt((-a + x)/(-a + b)))/pi, b >= x), (1, True))`

### Predicted fix
Add a `_cdf` method to ArcsinDistribution that returns the precomputed formula. Also add `asin` to imports.

### Edit sites
1. `sympy/stats/crv_types.py:48-50` — Add `asin` to the imports from sympy
2. `sympy/stats/crv_types.py:150-154` — Add `_cdf` method to ArcsinDistribution class

