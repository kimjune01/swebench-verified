# Hypothesis graph: sympy__sympy-13877

## Hypothesis Node 1 (Initial Diagnosis)

**Type:** Root cause identification  
**Status:** Active  
**Confidence:** Deduction - 95%

### Failure Summary
The test `test_determinant` fails because `M(5).det()` returns `nan` instead of `0`, and `M(6).det()` raises `TypeError: Invalid NaN comparison` instead of returning `0`.

The matrix `M(n) = [[i + a*j for i in range(n)] for j in range(n)]` has linearly dependent rows (each row is an arithmetic progression with the same common difference), so the determinant should be 0.

### Stack Trace Analysis
```
File "/testbed/sympy/core/exprtools.py", line 1179, in do
  if all(a.as_coeff_Mul()[0] < 0 for a in list_args):
File "/testbed/sympy/core/expr.py", line 336, in __lt__
  raise TypeError("Invalid NaN comparison")
```

### Root Cause
The Bareiss determinant algorithm computes intermediate matrix entries involving division by pivot values. When the matrix has linearly dependent rows, intermediate computations produce `0/0 = nan`. These nan values propagate through `cancel()` → `factor_terms()`. At line 1179 in `sympy/core/exprtools.py`, the code attempts to check if all coefficients are negative using:

```python
if all(a.as_coeff_Mul()[0] < 0 for a in list_args):
```

When `a.as_coeff_Mul()[0]` is `S.NaN`, the comparison `S.NaN < 0` raises `TypeError: Invalid NaN comparison` per the guard at `sympy/core/expr.py:336`.

### Supporting Evidence
1. `sympy/core/exprtools.py:1179` - The comparison that fails:
   ```python
   if all(a.as_coeff_Mul()[0] < 0 for a in list_args):
   ```

2. `sympy/core/expr.py:335-336` - The guard that raises the exception:
   ```python
   if me is S.NaN:
       raise TypeError("Invalid NaN comparison")
   ```

3. Verified that `S(0)/S(0) is S.NaN` returns `True`

4. Verified that `S.NaN.is_negative` returns `None` (doesn't raise exception)

### Edit Sites
- `sympy/core/exprtools.py` line 1179: Replace `< 0` comparison with `.is_negative` property check

The fix:
```python
# OLD:
if all(a.as_coeff_Mul()[0] < 0 for a in list_args):

# NEW:
if all(a.as_coeff_Mul()[0].is_negative for a in list_args):
```

**Rationale:** The `.is_negative` property returns `None` for nan (instead of raising exception), `True` for negative numbers, and `False` for non-negative numbers. In the `all()` check, `None` is falsy, so if any coefficient is nan, the check returns `False` and the optimization is skipped. This is the correct behavior: we cannot factor out a common negative sign if we cannot determine all coefficients are negative.

### Grep Verification
```bash
$ grep -rn "as_coeff_Mul.*< 0" sympy/
sympy/core/exprtools.py:1179:            if all(a.as_coeff_Mul()[0] < 0 for a in list_args):
```
This is the only occurrence of this pattern in the codebase.

### Rejected Hypotheses
None - this is the initial diagnosis.

### Open Questions
None - the fix is straightforward and well-scoped.

## Craft iteration 1 (RESOLVED)

**Hypothesis**: Recon diagnosis was correct - the issue has two components:
1. `factor_terms()` using `< 0` comparison raises TypeError on NaN
2. Bareiss algorithm using weak pivot selection generates NaN via 0/0

**Applied fixes**:
1. `sympy/core/exprtools.py:1179` - Changed `< 0` to `.is_negative`
2. `sympy/matrices/matrices.py` - Added `_is_zero_after_expand_mul` helper and updated Bareiss to use `_find_reasonable_pivot` with proper zero testing

**Gate result**: ✅ PASS
- 111 tests passed (was 110)
- 0 tests failed (was 1)  
- test_determinant now passes for M(5), M(6), M(7)

**Evidence trajectory**: Divergent-then-convergent
- First gate (exprtools fix only): Still failed with AssertionError (NaN result)
- Second gate (both fixes): PASS

**Codex volley**:
- Pre-gate: Codex correctly predicted exprtools fix alone was insufficient
- Post-failure: Codex identified need for Bareiss pivot fix
- Both predictions matched gate outcome

**Resolution**: RESOLVED - FAIL_TO_PASS tests pass, no PASS_TO_PASS regressions

## Audit: sympy__sympy-13877

### Patch Verification
Patch is live in working tree:
- `sympy/core/exprtools.py`: 2 lines changed
- `sympy/matrices/matrices.py`: 13 insertions, 11 deletions

### Gate Execution
Full test suite ran against patched code:
- 111 tests passed
- 3 skipped
- 4 expected to fail
- 39 exceptions (all pre-existing, confirmed against fail-on-base capture)

### FAIL_TO_PASS Analysis
- **test_determinant**: ✅ **PASS**
  - Previously failed with `nan` result for M(5) and TypeError for M(6)
  - Now correctly computes determinant = 0 for all cases

### PASS_TO_PASS Analysis
All PASS_TO_PASS tests verified passing:
- test_args, test_sum, test_abs, test_addition, test_fancy_index_matrix ✅
- test_creation, test_tolist, test_as_mutable, test_det_LU_decomposition ✅
- test_slicing, test_submatrix_assignment, test_extract, test_reshape ✅
- test_random, test_LUdecomp, test_LUsolve, test_matrix_inverse_mod ✅
- test_nullspace, test_columnspace, test_subs, test_xreplace ✅
- test_simplify, test_transpose, test_conjugate, test_conj_dirac ✅
- test_trace, test_shape, test_col_row_op, test_issue_3950 ✅
- test_issue_3981, test_evalf, test_is_symbolic, test_is_upper ✅
- test_is_lower, test_is_nilpotent, test_empty_zeros ✅
- test_nonvectorJacobian, test_vec, test_vech, test_vech_errors ✅
- test_diag, test_get_diag_blocks1, test_get_diag_blocks2 ✅
- All other PASS_TO_PASS tests: ✅

**Regressions**: none

### Pre-existing Failures (not counted)
The following 39 exceptions were confirmed against fail-on-base capture:
- test_normalize_sort_diogonalization (confirmed in base capture)
- test_issue_5320 (confirmed in base capture)
- test_pinv_solve (confirmed in base capture)
- test_issue_9422 (confirmed in base capture)
- test_as_real_imag (confirmed in base capture)
- test_deprecated (confirmed in base capture)
- Plus 33 other exceptions not in PASS_TO_PASS list
- All exceptions show DeprecationWarning for `collections.Iterable` - a Python 3.9 vs old codebase issue, not related to this patch

### Fix Validation
The patch correctly addresses both components identified in recon:
1. **exprtools.py**: Replaced `< 0` with `.is_negative` to handle NaN gracefully
2. **matrices.py**: Replaced weak pivot-finding with `_find_reasonable_pivot` using `_is_zero_after_expand_mul` to properly detect symbolic zeros

No over-broad changes. No unintended side effects.

VERDICT: RESOLVED
RE-ENTER: none
