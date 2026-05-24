# Hypothesis graph: scikit-learn__scikit-learn-14710

## H0: Test fails due to type mismatch in accuracy_score (abduction, 85%)

**Observation**: test_string_target_early_stopping[None] fails with:
```
TypeError: '<' not supported between instances of 'str' and 'float'
```
in numpy's `_unique1d` called from `accuracy_score` → `_check_targets` → `np.union1d(y_true, y_pred)`.

**Evidence from stack trace**:
- `gradient_boosting.py:430` calls `self.scorer_(self, X_binned_small_train, y_small_train)`
- scorer is `_passthrough_scorer` which calls `estimator.score(X, y)`
- `base.py:368` score() calls `accuracy_score(y, self.predict(X))`
- `y` contains encoded values (0.0, 1.0)
- `self.predict(X)` returns decoded strings ('x', 'y')
- numpy fails to sort mixed array of floats and strings

**Root cause**: In `gradient_boosting.py`:
- Line 105: `y = self._encode_y(y)` encodes string labels to numeric (0, 1)
- Line 145-150: encoded y is split into y_train, y_val
- Lines 429-430, 434-436 in `_check_early_stopping_scorer`: encoded y values are passed to scorer
- Scorer calls `estimator.score(X, encoded_y)` which compares encoded y against decoded predictions

**Why test[loss] passes**: When `scoring='loss'`, the code path uses `_check_early_stopping_loss` (line 233) which passes raw_predictions and encoded y to the loss function. Loss functions work with encoded values, so no type mismatch.

**Edit sites**:
- `sklearn/ensemble/_hist_gradient_boosting/gradient_boosting.py` lines 423-440 (_check_early_stopping_scorer method): decode y_small_train and y_val before passing to scorer, but only for classifiers (check hasattr(self, 'classes_'))


## craft: iteration 1 — CONVERGENT (GREEN)

**Applied fix:**
- Modified `_check_early_stopping_scorer` in `sklearn/ensemble/_hist_gradient_boosting/gradient_boosting.py` (lines 426-446)
- Added conditional decoding of y_small_train and y_val before passing to scorer
- Used `hasattr(self, 'classes_')` to detect classifiers
- Cast to integer with `.astype(np.intp)` before indexing (codex caught this - y arrays are float dtype)

**codex volley (pre-gate):**
- Identified IndexError risk: y arrays are float, need `.astype(np.intp)` before using as indices
- Confirmed fix is in right location conceptually
- Suggested helper method to avoid duplication (deferred as not minimal)

**Gate result:** ✅ PASS
- FAIL_TO_PASS test now passes: `test_string_target_early_stopping[None]`
- All 80 tests passed, 1 warning

**e-value trajectory:** CONVERGENT-GREEN (first attempt success)


## Audit: scikit-learn__scikit-learn-14710

### Patch confirmed live
```
sklearn/ensemble/_hist_gradient_boosting/gradient_boosting.py | 14 ++++++++++++--
1 file changed, 12 insertions(+), 2 deletions(-)
```

### FAIL_TO_PASS
- `test_string_target_early_stopping[None]`: **PASSED** ✓

### PASS_TO_PASS regressions
**None** - all PASS_TO_PASS tests remain passing.

### Pre-existing failures (not counted)
**None** - no pre-existing failures observed.

### Gate summary
- 80 tests passed, 0 failed, 1 warning
- FAIL_TO_PASS test now passing
- Zero regressions introduced

### Kill report
Not applicable - patch is RESOLVED.

The fix correctly decodes encoded labels before passing to the scorer in classifiers, aligning encoded y values with the decoded predictions from `predict()`. The hasattr check ensures the fix only applies to classifiers, leaving regressors unaffected.

VERDICT: RESOLVED
RE-ENTER: none
