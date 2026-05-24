# Hypothesis graph: sympy__sympy-21379

## H1: Mod.eval unconditionally calls gcd on Piecewise expressions (deduction, 98%)

**Symptom**: `PolynomialError: Piecewise generators do not make sense` when evaluating `(Piecewise(...) / z) % 1`

**Root cause**: `sympy/core/mod.py:169` calls `gcd(p, q)` without checking if p or q contains Piecewise. The gcd function tries to convert expressions to polynomial form, which fails for Piecewise because they cannot be polynomial generators.

**Evidence**:
- Stack trace: `Mod.eval:169` → `gcd()` → `parallel_poly_from_expr()` → error at `polytools.py:4399`
- `sympy/polys/polytools.py:4397-4399` explicitly checks and rejects Piecewise generators
- Other code (e.g., `basic.py:632`, `expr.py:3372`) uses `.has(Piecewise)` to guard polynomial operations

**Fix**: Check `p.has(Piecewise) or q.has(Piecewise)` before calling gcd. If true, set `G = S.One` and skip gcd extraction.

**Status**: Primary hypothesis

## craft gate loop

### Iteration 1: Draft + codex volley

**Draft approach:** Guard gcd call with `p.has(Piecewise) or q.has(Piecewise)` check, skip GCD extraction when Piecewise detected.

**Codex feedback:** 
- Guard too narrow — issue is `gcd()` raising PolynomialError for non-polynomial expressions, not Piecewise specifically
- Importing Piecewise creates layering violation (core importing elementary functions)
- Better to catch PolynomialError exception than pre-detect Piecewise
- Suggested fix:
```python
from sympy.polys.polyerrors import PolynomialError

try:
    G = gcd(p, q)
except PolynomialError:
    G = S.One

if G != 1:
    p, q = [
        gcd_terms(i/G, clear=False, fraction=False) for i in (p, q)]
```

**Revision:** Applied exception-based approach to `sympy/core/mod.py:170-177`

### Iteration 1: Gate result

**Status:** PASS ✓

**Output:** All 93 tests passed, including test_Mod

**Resolution:** The PolynomialError exception handler successfully prevents the crash when Mod.eval() encounters Piecewise (or any other non-polynomial) expressions in the gcd call. Setting G to S.One when the exception occurs skips the GCD extraction without breaking the remainder of the evaluation logic.

## Audit: sympy__sympy-21379

### Phase 1: Patch confirmed live
```
 sympy/core/mod.py | 6 +++++-
 1 file changed, 5 insertions(+), 1 deletion(-)
```

### Phase 2: Gate execution
All 93 tests passed, 2 expected to fail (pre-existing).

### Phase 3: Classification

**FAIL_TO_PASS**:
- test_Mod: **PASS** ✓

**PASS_TO_PASS regressions**: none

**Pre-existing (not counted, confirmed against base capture)**:
- test_evenness_in_ternary_integer_product_with_odd (marked `f` on base and gate)
- test_oddness_in_ternary_integer_product_with_odd (marked `f` on base and gate)

### Phase 4: Verdict

All FAIL_TO_PASS tests pass (1/1). Zero PASS_TO_PASS regressions.

**VERDICT: RESOLVED**
**RE-ENTER: none**

