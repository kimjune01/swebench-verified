# Hypothesis graph: scikit-learn__scikit-learn-14894

## H₀: Division by zero when constructing dual_coef_ with empty support vectors (abduction)

**Observation**: Test `test_sparse_fit_support_vectors_empty` fails with `ZeroDivisionError` at `sklearn/svm/base.py:291`

**Failure mode**: Exception raised during sparse matrix construction

**Call path**: 
- `SVR.fit()` → `_sparse_fit()` → line 291: `np.arange(0, 1, 0)` when computing `dual_coef_indptr`

**Root cause**: When `n_SV = 0` (no support vectors):
- Line 289: `dual_coef_indices = np.tile(np.arange(0), n_class)` produces empty array
- Line 290-291: `dual_coef_indptr = np.arange(0, 0 + 1, 0 / n_class)` becomes `np.arange(0, 1, 0.0)`
- numpy raises `ZeroDivisionError` when step is 0

**Supporting evidence**:
- `sklearn/svm/base.py:289`: `dual_coef_indices = np.tile(np.arange(n_SV), n_class)` 
- `sklearn/svm/base.py:290-291`: Division by `n_class` produces 0 when indices are empty
- Verified: `python -c "import numpy as np; np.arange(0, 1, 0)"` raises ZeroDivisionError
- Test expects empty sparse matrices when no support vectors exist

**Confidence**: deduction — 99% (traced execution, reproduced error, verified numpy behavior)

## craft gate-loop iteration 1

**Diff applied:**
```python
# sklearn/svm/base.py lines 289-297
if n_SV == 0:
    self.dual_coef_ = sp.csr_matrix((n_class, 0), dtype=dual_coef_data.dtype)
else:
    dual_coef_indices = np.tile(np.arange(n_SV), n_class)
    dual_coef_indptr = np.arange(0, dual_coef_indices.size + 1,
                                 dual_coef_indices.size / n_class)
    self.dual_coef_ = sp.csr_matrix(
        (dual_coef_data, dual_coef_indices, dual_coef_indptr),
        (n_class, n_SV))
```

**codex pre-gate review:** No functional blocker. Suggested dtype preservation to match dual_coef_data.dtype (incorporated).

**Gate result:** GREEN - all 86 tests passed including test_sparse_fit_support_vectors_empty

**Trajectory:** Convergent (resolved) - FAIL_TO_PASS test now passes, no regressions

**Resolution:** The fix handles the n_SV==0 edge case by constructing an empty CSR matrix directly, avoiding the ZeroDivisionError from np.arange(0, 1, 0.0). The dtype preservation ensures consistency with the libsvm output.

---

# Audit: scikit-learn__scikit-learn-14894

## FAIL_TO_PASS
- `sklearn/svm/tests/test_svm.py::test_sparse_fit_support_vectors_empty`: **PASS** ✓

## PASS_TO_PASS regressions
None — all 86 tests passed, including all PASS_TO_PASS tests.

## Pre-existing (not counted, confirmed against base capture)
None — baseline showed ZeroDivisionError in one test, all other tests passing. Current run shows all tests passing.

## Summary
The patch successfully resolves the issue:
- **FAIL_TO_PASS**: 1/1 passing (100%)
- **PASS_TO_PASS**: 85/85 passing (100%)  
- **Regressions**: 0
- **Pre-existing failures**: 0

The fix guards against n_SV==0 by constructing an empty CSR matrix directly, preventing the ZeroDivisionError that occurred when computing `dual_coef_indptr` with step size 0.
