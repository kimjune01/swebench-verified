# Hypothesis graph: scikit-learn__scikit-learn-11578

## H₀ (abduction): Initial symptom
**Status:** Confirmed  
**Mode:** Abduction  
**Confidence:** 100% (observed)

The test `test_logistic_cv_multinomial_score[neg_log_loss-multiclass_agg_list3]` fails with:
```
AssertionError: 
Arrays are not almost equal to 6 decimals

Mismatched elements: 1 / 1 (100%)
Max absolute difference: 0.04312538
Max relative difference: 0.05731496
 x: array(-0.795553)
 y: array(-0.752428)
```

The test expects the score from `_log_reg_scoring_path()` to match the score from a fitted `LogisticRegression(multi_class='multinomial')` when using the `neg_log_loss` scorer.

**Evidence:**
- `sklearn/linear_model/tests/test_logistic.py:526` — assertion failure
- Test creates LR with `multi_class='multinomial'`, extracts params, calls `_log_reg_scoring_path()` with those params
- Expects scores to match, but they differ by ~0.043

## H₁ (deduction): Root cause is missing multi_class parameter
**Status:** Confirmed  
**Mode:** Deduction  
**Confidence:** 98%

The `_log_reg_scoring_path()` function creates a `LogisticRegression` instance at line 925 without passing the `multi_class` parameter, even though the function receives it as an argument.

**Code path:**
1. `_log_reg_scoring_path()` receives `multi_class='multinomial'` as parameter (line 782)
2. Line 925: `log_reg = LogisticRegression(fit_intercept=fit_intercept)` — multi_class NOT passed
3. LogisticRegression defaults to `multi_class='ovr'` (line 1165 in __init__)
4. Line 967: `scores.append(scoring(log_reg, X_test, y_test))`
5. The `neg_log_loss` scorer calls `log_reg.predict_proba(X_test)`
6. `predict_proba()` branches on `self.multi_class` (line 1342):
   - If 'ovr': uses `_predict_proba_lr()` (logistic sigmoid + normalization)
   - If 'multinomial': uses `softmax(decision_function)` (line 1351)
7. These produce different probability estimates, hence different scores

**Evidence:**
- `sklearn/linear_model/logistic.py:925` — `log_reg = LogisticRegression(fit_intercept=fit_intercept)`
- `sklearn/linear_model/logistic.py:1165` — default `multi_class='ovr'` in __init__
- `sklearn/linear_model/logistic.py:1342-1351` — predict_proba branches on multi_class
- `sklearn/linear_model/logistic.py:1323-1328` — docstring confirms different approaches

## Fix specification
**Edit site:** `sklearn/linear_model/logistic.py:925`

Change:
```python
log_reg = LogisticRegression(fit_intercept=fit_intercept)
```

To:
```python
log_reg = LogisticRegression(fit_intercept=fit_intercept, multi_class=multi_class)
```

This ensures the temporary LogisticRegression instance used for scoring inherits the multi_class setting from the function parameters, so predict_proba uses the correct probability computation method.

## Craft: Gate Loop

### Iteration 1

**Hypothesis**: Line 925 missing `multi_class=multi_class` parameter in LogisticRegression constructor

**Edit applied**:
```diff
--- a/sklearn/linear_model/logistic.py
+++ b/sklearn/linear_model/logistic.py
@@ -925 +925
-    log_reg = LogisticRegression(fit_intercept=fit_intercept)
+    log_reg = LogisticRegression(fit_intercept=fit_intercept, multi_class=multi_class)
```

**Codex review**: Fix is directionally correct. The temporary LogisticRegression instance needs `multi_class` to match the path that produced the coefficients. Should not break OvR or multinomial scoring.

**Gate outcome**: ✅ PASS — All 94 tests passed, including `test_logistic_cv_multinomial_score[neg_log_loss-multiclass_agg_list3]`

**Resolution**: The fix correctly propagates the `multi_class` parameter to the temporary LogisticRegression instance used for scoring, ensuring that `predict_proba()` uses the same approach (softmax for multinomial, sigmoid+normalization for OvR) as the fitted model being compared against.

## Audit: scikit-learn__scikit-learn-11578

**Patch status**: Live — 1 file changed, 1 insertion(+), 1 deletion(-)

**Gate results**: All 94 tests passed in 3.16s

### FAIL_TO_PASS
- `test_logistic_cv_multinomial_score[neg_log_loss-multiclass_agg_list3]`: **PASS** ✓

### PASS_TO_PASS regressions
None — all PASS_TO_PASS tests passed successfully.

### Pre-existing failures (not counted)
None — the baseline showed only the F2P test failing, which now passes.

### Verdict
All FAIL_TO_PASS tests pass (1/1) and zero PASS_TO_PASS regressions (0 regressions out of 93 tests). The fix successfully resolved the issue by ensuring the temporary LogisticRegression instance in `_log_reg_scoring_path()` receives the `multi_class` parameter, making its `predict_proba()` behavior consistent with the fitted model being scored against.

VERDICT: RESOLVED
RE-ENTER: none
