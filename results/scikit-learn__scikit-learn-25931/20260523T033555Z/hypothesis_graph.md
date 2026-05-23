# Hypothesis graph: scikit-learn__scikit-learn-25931

## H₁: Feature names validation triggered during internal score_samples call in fit

**Type:** Root cause (deduction)
**Confidence:** 95%

**Observation:**
Test `test_iforest_preserve_feature_names` fails with UserWarning: "X does not have valid feature names, but IsolationForest was fitted with feature names" when fitting IsolationForest with a pandas DataFrame and `contamination != "auto"`.

Stack trace shows:
- `fit()` → line 348: `self.score_samples(X)`
- `score_samples()` → line 436: `self._validate_data(X, ..., reset=False)`
- `_validate_data()` → `_check_feature_names(X, reset=False)` in base.py
- `_check_feature_names()` → line 451: raises warning

**Root cause:**
At `_iforest.py:291`, `X = self._validate_data(X, ...)` converts the input DataFrame to a numpy array and sets `self.feature_names_in_`. When `contamination != "auto"`, at line 348, `self.score_samples(X)` is called with this numpy array. Inside `score_samples` at line 436, `_validate_data(..., reset=False)` triggers a feature names consistency check. Since X is now a numpy array (no feature names) but the model has `feature_names_in_` set, the warning is raised.

**Evidence:**
- `_iforest.py:291` — First validation: `X = self._validate_data(X, accept_sparse=["csc"], dtype=tree_dtype)` sets feature_names_in_ and converts DataFrame to array
- `_iforest.py:348` — Internal call: `self.offset_ = np.percentile(self.score_samples(X), 100.0 * self.contamination)` passes numpy array
- `_iforest.py:436` — Re-validation: `X = self._validate_data(X, accept_sparse="csr", dtype=np.float32, reset=False)` triggers feature names check
- `base.py:451` — Check fails: X is ndarray (no feature names) but model has feature_names_in_

**Fix:**
Replace line 348's call to `score_samples(X)` with a direct call to the internal `_compute_chunked_score_samples(X)` method after converting X to the expected format (csr sparse or ndarray, float32 dtype). This bypasses the unnecessary re-validation.

**Edit sites:**
- `sklearn/ensemble/_iforest.py:348` — Replace `self.score_samples(X)` call with direct computation using `_compute_chunked_score_samples`


## Craft Gate Loop

### Iteration 1: Initial Fix Applied

**Hypothesis**: The feature names warning is triggered because `fit()` calls `self.score_samples(X)` with an already-validated numpy array (which has lost its feature names), and `score_samples()` re-validates with `reset=False`, triggering the feature names consistency check.

**Implementation**: Replaced the call to `self.score_samples(X)` in the `fit()` method (line 348) with direct computation:
1. Convert X to csr format (if sparse) and float32 dtype
2. Call `scores = -self._compute_chunked_score_samples(X_score)` directly
3. Compute offset from scores

**Gate Result**: ✅ GREEN - All 22 tests passed including `test_iforest_preserve_feature_names`

**Evidence Classification**: Convergent success - the fix directly addressed the root cause and all tests pass.

**Trajectory**: The recon diagnosis was accurate. By bypassing the public `score_samples()` API method and calling the internal `_compute_chunked_score_samples()` directly, we avoid the unnecessary re-validation that was triggering the feature names warning. The fix is minimal and only affects the specific code path when `contamination != "auto"`.

**Resolution**: FIXED - The FAIL_TO_PASS test now passes, and no existing tests were broken.

---

# Audit: scikit-learn__scikit-learn-25931

## FAIL_TO_PASS
- `sklearn/ensemble/tests/test_iforest.py::test_iforest_preserve_feature_names`: **PASS** ✅

## PASS_TO_PASS regressions
**None** — All 21 PASS_TO_PASS tests continue to pass.

## Pre-existing failures (not counted, confirmed against base capture)
**None** — The FAIL_TO_PASS test was the only failure on base, and it now passes.

## Patch Analysis

The craft patch successfully resolves the issue by:

1. **Root cause addressed**: The problem was that `fit()` was calling the public `score_samples(X)` method at line 348, which re-validates input with `reset=False`, triggering a feature names consistency check that fails because X has been converted to a numpy array (losing feature names).

2. **Fix implemented**: Replaced the call to `score_samples(X)` with direct score computation:
   ```python
   # Convert X to expected format (csr sparse if needed, float32 dtype)
   if issparse(X):
       X_score = X.tocsr().astype(np.float32)
   else:
       X_score = X.astype(np.float32)
   # Call internal method directly to bypass validation
   scores = -self._compute_chunked_score_samples(X_score)
   self.offset_ = np.percentile(scores, 100.0 * self.contamination)
   ```

3. **Impact**: Minimal, surgical change affecting only the contamination offset calculation path when `contamination != "auto"`. No behavioral changes to scoring logic—just eliminates the unnecessary re-validation.

## Gate Results Summary
- **Total tests**: 22
- **Passed**: 22
- **Failed**: 0
- **FAIL_TO_PASS resolved**: 1/1 (100%)
- **PASS_TO_PASS regressions**: 0/21 (0%)

VERDICT: RESOLVED
RE-ENTER: none
