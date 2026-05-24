# Hypothesis graph: sympy__sympy-23824

## H₀: Initial observation (abduction)
The test `test_kahane_simplify1` fails because `kahane_simplify()` reverses the order of leading uncontracted gamma matrices when they appear before contracted ones.

**Evidence:**
- Test case: `G(rho)*G(sigma)*G(mu)*G(-mu)` simplifies to `4*G(sigma)*G(rho)` instead of `4*G(rho)*G(sigma)`
- The contracted pair `G(mu)*G(-mu)` correctly simplifies to factor of 4
- But leading free indices `rho, sigma` appear in reversed order in result

**Classification:** abduction (60-85% confidence from pattern matching)

## H₁: Root cause identified (deduction)
The bug is in `kahane_simplify()` at lines 697-698. Leading free gamma matrices (those before the first contracted pair) are removed, then re-inserted at the end of the algorithm. The re-insertion loop iterates forward but inserts at position 0, causing reversal.

**Evidence from code:**
- `sympy/physics/hep/gamma_matrices.py:697-698`:
  ```python
  for i in range(0, first_dum_pos):
      [ri.insert(0, free_pos[i]) for ri in resulting_indices]
  ```

**Why this causes reversal:**
- If `first_dum_pos = 2` and `free_pos = [rho, sigma, ...]`
- Iteration i=0: insert `free_pos[0]=rho` at position 0 → `[rho]`
- Iteration i=1: insert `free_pos[1]=sigma` at position 0 → `[sigma, rho]`
- Result: reversed order

**Experimental confirmation:**
```
Test: G(rho)*G(sigma)*G(mu)*G(-mu)
Result: 4*GammaMatrix(sigma)*GammaMatrix(rho)  ← WRONG ORDER
Expected: 4*GammaMatrix(rho)*GammaMatrix(sigma)
```

**Classification:** deduction (95-99% confidence - traced code path and confirmed with test)

## Edit site
- `sympy/physics/hep/gamma_matrices.py:697` - Change loop to iterate in reverse order:
  ```python
  for i in range(first_dum_pos - 1, -1, -1):
  ```
  This preserves the original order when inserting at position 0.

**No competing hypotheses** - the bug is localized to a single loop with clear causality.

**No rejected hypotheses** - the problem statement correctly identified the location.


## craft gate loop

### Iteration 1 (PASS)

**Diff applied:**
```diff
--- a/sympy/physics/hep/gamma_matrices.py
+++ b/sympy/physics/hep/gamma_matrices.py
@@ -694,7 +694,7 @@ def kahane_simplify(expression):
 
     # If `first_dum_pos` is not zero, it means that there are trailing free gamma
     # matrices in front of `expression`, so multiply by them:
-    for i in range(0, first_dum_pos):
+    for i in range(first_dum_pos - 1, -1, -1):
         [ri.insert(0, free_pos[i]) for ri in resulting_indices]
 
     resulting_expr = S.Zero
```

**Codex review:** Confirmed correct. The reversed iteration order fixes the prepending logic to preserve input order of leading free gamma matrices.

**Gate result:** ✅ GREEN - All 4 tests passed including `test_kahane_simplify1`

**Resolution:** The fix correctly addresses the root cause. Reversing the loop iteration order from `range(0, first_dum_pos)` to `range(first_dum_pos - 1, -1, -1)` ensures that when elements are inserted at position 0, they maintain their original order instead of being reversed.

## Audit: sympy__sympy-23824

### FAIL_TO_PASS
- `test_kahane_simplify1`: **PASS** ✓

### PASS_TO_PASS
- `test_kahane_algorithm`: **ok** ✓
- `test_gamma_matrix_class`: **ok** ✓

### PASS_TO_PASS regressions
none

### Pre-existing failures (not counted, confirmed against base capture)
none

### Verdict analysis
All FAIL_TO_PASS tests now pass. All PASS_TO_PASS tests remain passing. Zero regressions introduced. The patch successfully resolves the issue.

**Gate output:**
```
test_kahane_algorithm ok
test_kahane_simplify1 ok
test_gamma_matrix_class ok
test_gamma_matrix_trace ok
================== tests finished: 4 passed, in 5.48 seconds ===================
```

**Baseline comparison:**
- test_kahane_simplify1: F (base) → ok (patched) — **fixed** ✓
- test_kahane_algorithm: ok (base) → ok (patched) — **stable** ✓
- test_gamma_matrix_class: ok (base) → ok (patched) — **stable** ✓

VERDICT: RESOLVED
RE-ENTER: none
