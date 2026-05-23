# Hypothesis graph: scikit-learn__scikit-learn-14629

## H₀: Missing classes_ attribute (abduction)

**Observation**: Test fails with `AttributeError: 'MultiOutputClassifier' object has no attribute 'classes_'` at `sklearn/tests/test_multioutput.py:542`.

**Root cause**: `MultiOutputClassifier` does not expose a `classes_` attribute, but the test (and `cross_val_predict`) expects it to be a list of class arrays (one per output).

**Evidence**:
- `sklearn/multioutput.py:300-393`: `MultiOutputClassifier` inherits from `MultiOutputEstimator` but doesn't override `fit` to set `classes_`
- `sklearn/multioutput.py:579-583`: `ClassifierChain.fit()` explicitly sets `self.classes_ = [estimator.classes_ for chain_idx, estimator in enumerate(self.estimators_)]`
- `sklearn/model_selection/_validation.py:859`: `cross_val_predict` accesses `estimator.classes_[i_label]` when predictions is a list
- Manual test: `RandomForestClassifier` (native multi-output support) has `classes_` as a list; `MultiOutputClassifier` does not

**Hypothesis**: The fix is to override `fit()` in `MultiOutputClassifier` to set `self.classes_ = [estimator.classes_ for estimator in self.estimators_]` after calling `super().fit()`.

**Confidence**: Deduction — 95% (traced code path, verified with manual test, pattern matches ClassifierChain)


## Craft Gate Loop - Iteration 1

**Hypothesis**: MultiOutputClassifier needs `classes_` attribute aggregated from individual estimators.

**Implementation**: Added `fit` and `partial_fit` methods to `MultiOutputClassifier` that:
1. Call `super().fit()` / `super().partial_fit()` to train individual estimators
2. Set `self.classes_ = [estimator.classes_ for estimator in self.estimators_]`
3. Also added `classes_` to the Attributes documentation

**Codex Review**: Approved with recommendation to keep both fit and partial_fit for consistency.

**Gate Result**: ✅ PASS - All 27 tests pass including the target test `test_multi_output_classes_[estimator1]`

**Trajectory**: Convergent (green on first attempt)

**Status**: RESOLVED

---

# Audit: scikit-learn__scikit-learn-14629

## FAIL_TO_PASS
- `test_multi_output_classes_[estimator1]`: **PASS** ✓

## PASS_TO_PASS regressions
None

## Pre-existing (not counted, confirmed against base capture)
None

## Resolution Summary
The patch successfully resolves the issue by adding the `classes_` attribute to `MultiOutputClassifier.fit()`:
```python
self.classes_ = [estimator.classes_ for estimator in self.estimators_]
```

All 27 tests pass. The previously failing test now passes, and no regressions were introduced.

VERDICT: RESOLVED
RE-ENTER: none
