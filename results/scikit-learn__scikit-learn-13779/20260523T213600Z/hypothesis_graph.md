# Hypothesis graph: scikit-learn__scikit-learn-13779

## H₀: Initial Abduction (2026-05-23)

**Hypothesis:** The tests fail because `_BaseVoting.fit` calls `has_fit_parameter(step, 'sample_weight')` on all estimators without checking if `step is None` first, causing `AttributeError: 'NoneType' object has no attribute 'fit'`.

**Mode:** Deduction (95%)

**Evidence:**
- Stack trace shows failure at `sklearn/utils/validation.py:808` in `has_fit_parameter`: `return parameter in signature(estimator.fit).parameters`
- Call path: `VotingRegressor.fit:451` → `_BaseVoting.fit:81` → `has_fit_parameter`
- `sklearn/ensemble/voting.py:79-83`: sample_weight validation loop iterates all estimators without None check
- `sklearn/ensemble/voting.py:96`: later in same method, None estimators are properly filtered: `for clf in clfs if clf is not None`
- Test successfully calls `voter.set_params(lr=None)` then `voter.fit(X, y, sample_weight=np.ones(y.shape))` - confirming None estimator with sample_weight triggers the bug

**Edit site:**
- `sklearn/ensemble/voting.py:81` - add `step is not None and` before `has_fit_parameter(step, 'sample_weight')`

**Competing hypotheses:** None

**Rejected hypotheses:** None

## Gate iteration 1 (craft)

**Hypothesis**: Add None check before calling `has_fit_parameter` at line 81 in `sklearn/ensemble/voting.py`

**Change applied**:
```diff
--- a/sklearn/ensemble/voting.py
+++ b/sklearn/ensemble/voting.py
@@ -78,7 +78,7 @@ class _BaseVoting(_BaseComposition, TransformerMixin):
 
         if sample_weight is not None:
             for name, step in self.estimators:
-                if not has_fit_parameter(step, 'sample_weight'):
+                if step is not None and not has_fit_parameter(step, 'sample_weight'):
                     raise ValueError('Underlying estimator \'%s\' does not'
                                      ' support sample weights.' % name)
```

**codex review**: Functional behavior correct; None estimators properly skipped during sample_weight validation, consistent with the skip at line 96 during fitting.

**Gate result**: GREEN - All 20 tests passed including both FAIL_TO_PASS:
- test_none_estimator_with_weights[X0-y0-voter0] ✓
- test_none_estimator_with_weights[X1-y1-voter1] ✓

**Trajectory**: Convergent-success (first iteration)

---

# Audit: scikit-learn__scikit-learn-13779

## FAIL_TO_PASS
- `test_none_estimator_with_weights[X0-y0-voter0]`: **PASS** ✓
- `test_none_estimator_with_weights[X1-y1-voter1]`: **PASS** ✓

## PASS_TO_PASS regressions
None - all 18 PASS_TO_PASS tests passed cleanly.

## Pre-existing (not counted, confirmed against base capture)
None - all tests that passed were expected to pass.

## Summary
The patch successfully resolves the issue. The single-line change adds a None check (`step is not None and`) before calling `has_fit_parameter(step, 'sample_weight')` at line 81 in `sklearn/ensemble/voting.py`. This prevents the AttributeError when an estimator is set to None while using sample_weight.

All 20 tests in the test suite passed:
- Both FAIL_TO_PASS tests now pass
- All 18 PASS_TO_PASS tests continue to pass
- Zero regressions introduced

VERDICT: RESOLVED
RE-ENTER: none
