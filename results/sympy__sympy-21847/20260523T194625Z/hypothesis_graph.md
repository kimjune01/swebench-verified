# Hypothesis graph: sympy__sympy-21847

## H₀: Initial diagnosis (abduction)

**Hypothesis**: The `itermonomials` function incorrectly filters monomials by checking if the maximum power of any single variable is >= min_degree, when it should check if the total degree (sum of all variable powers) is in the range [min_degree, max_degree].

**Evidence**:
- Test failure: `assert set(itermonomials([x, y], 3, 3)) == {x**3, x**2*y, x*y**2, y**3}` fails
- Current output: `{x**3, y**3}` (only monomials where a single variable has power >= 3)
- Missing: `x**2*y, x*y**2` (total degree 3, but max individual power is 2)

**Root cause location**:
- `sympy/polys/monomials.py:130` (commutative variables)
- `sympy/polys/monomials.py:142` (non-commutative variables)
- Both lines: `if max(powers.values()) >= min_degree:`

**Proposed fix**:
- Change condition from `max(powers.values()) >= min_degree`
- To: `sum(powers.values()) >= min_degree` (or `min_degree <= sum(powers.values()) <= max_degree`)

**Confidence**: Deduction - 95%
- Traced through the code path from test to failure point
- Confirmed by manual simulation of the algorithm
- Bug is in the filter condition, not the generation logic

**Reasoning mode**: Deduction (traced code execution and compared against documented behavior)


## /craft gate loop - iteration 1

**Diff applied:**
```diff
--- a/sympy/polys/monomials.py
+++ b/sympy/polys/monomials.py
@@ -127,7 +127,7 @@ def itermonomials(variables, max_degrees, min_degrees=None):
                 for variable in item:
                     if variable != 1:
                         powers[variable] += 1
-                if max(powers.values()) >= min_degree:
+                if sum(powers.values()) >= min_degree:
                     monomials_list_comm.append(Mul(*item))
             yield from set(monomials_list_comm)
         else:
@@ -139,7 +139,7 @@ def itermonomials(variables, max_degrees, min_degrees=None):
                 for variable in item:
                     if variable != 1:
                         powers[variable] += 1
-                if max(powers.values()) >= min_degree:
+                if sum(powers.values()) >= min_degree:
                     monomials_list_non_comm.append(Mul(*item))
             yield from set(monomials_list_non_comm)
     else:
```

**codex pre-gate review:** Core change correct - `sum(powers.values())` matches documented total-degree filter. No regressions expected.

**Gate result:** ✅ PASS - all 11 tests passed including `test_monomials`

**Trajectory:** Convergent-success on first iteration

**Resolution:** Changed `max(powers.values()) >= min_degree` to `sum(powers.values()) >= min_degree` at lines 130 and 142. The bug was checking maximum individual power instead of total degree (sum of all powers). Fix validated by gate.


## /audit verification

**Patch status**: Live in working tree (2 insertions, 2 deletions in `sympy/polys/monomials.py`)

**Gate execution**: All 11 tests passed

### FAIL_TO_PASS results:
- `test_monomials`: ✅ **PASS** (was failing on base, now passing)

### PASS_TO_PASS results:
- `test_monomial_count`: ✅ PASS
- `test_monomial_mul`: ✅ PASS
- `test_monomial_div`: ✅ PASS
- `test_monomial_gcd`: ✅ PASS
- `test_monomial_lcm`: ✅ PASS
- `test_monomial_max`: ✅ PASS
- `test_monomial_pow`: ✅ PASS
- `test_monomial_min`: ✅ PASS
- `test_monomial_divides`: ✅ PASS

### Regressions:
None

### Pre-existing failures (not counted):
None

**Classification**: All FAIL_TO_PASS tests now pass, all PASS_TO_PASS tests still pass, zero regressions.

**Verdict**: RESOLVED
**Route**: none (fix is complete and verified)
