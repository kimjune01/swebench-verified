# Hypothesis graph: scikit-learn__scikit-learn-25973

## H0: Generator exhaustion causes empty scores list (Iteration 1)

**Type**: Abduction  
**Confidence**: 90% (induction from code trace)

### Diagnosis
When a generator is passed as the `cv` parameter to `SequentialFeatureSelector`, it gets exhausted after the first call to `cross_val_score` within `_get_best_new_feature_score`. Subsequent calls receive an exhausted generator, resulting in an empty list when `_CVIterableWrapper` tries to consume it.

### Call trace
1. `SequentialFeatureSelector.fit()` stores the generator in `self.cv`
2. `fit()` calls `_get_best_new_feature_score()` multiple times (once per candidate feature)
3. Each call does `cross_val_score(..., cv=self.cv, ...)`
4. First call: `cross_val_score` → `cross_validate` → `check_cv(self.cv)` wraps generator in `_CVIterableWrapper(generator)` which does `list(generator)`, consuming it
5. Subsequent calls: `check_cv(exhausted_generator)` → `_CVIterableWrapper(exhausted_generator)` → `list(exhausted_generator)` = `[]`
6. `cross_validate` iterates over empty list, producing `results = []`
7. `_aggregate_score_dicts([])` tries `scores[0]`, raising `IndexError: list index out of range`

### Evidence
- `_CVIterableWrapper.__init__` at `sklearn/model_selection/_split.py:2357` consumes iterables via `self.cv = list(cv)`
- `check_cv` at `_split.py:2456` wraps iterables without `.split()` method in `_CVIterableWrapper`
- Generators have no `.split()` method and are iterables, so they get wrapped
- Generators can only be consumed once

### Precedent
`RFECV` in `sklearn/feature_selection/_rfe.py:689` normalizes `cv` once in `fit()`:
```python
cv = check_cv(self.cv, y, classifier=is_classifier(self.estimator))
```

### Root cause
`SequentialFeatureSelector` does not normalize the `cv` parameter before reusing it multiple times, unlike similar estimators.

### Edit sites
1. `sklearn/feature_selection/_sequential.py` line 16: Add imports
   - Add `check_cv` to model_selection imports
   - Add `is_classifier` from `..base`

2. `sklearn/feature_selection/_sequential.py` lines 260-280 (in `fit` method after validation): Normalize cv
   - After `X = self._validate_data(...)`, call:
     ```python
     cv = check_cv(self.cv, y, classifier=is_classifier(self.estimator))
     ```

3. `sklearn/feature_selection/_sequential.py` line 296 (method signature): Update `_get_best_new_feature_score`
   - Add `cv` parameter to signature

4. `sklearn/feature_selection/_sequential.py` line 277 (call site): Pass normalized cv
   - Update call to pass `cv` argument

5. `sklearn/feature_selection/_sequential.py` line 308 (usage): Use parameter instead of self.cv
   - Change `cv=self.cv` to `cv=cv`

## Craft gate-loop iteration 1

**Action**: Applied fix based on recon diagnosis:
1. Added imports: `is_classifier` from `..base`, `check_cv` from `..model_selection`
2. Normalized cv parameter once in `fit()` method after `cloned_estimator = clone(self.estimator)`:
   ```python
   cv = check_cv(self.cv, y, classifier=is_classifier(cloned_estimator))
   ```
3. Updated `_get_best_new_feature_score` signature to accept `cv` parameter
4. Updated call site in `fit()` to pass normalized `cv`
5. Updated `cross_val_score` call to use `cv=cv` instead of `cv=self.cv`

**Codex pre-gate review**: Caught minor issue - recommended using `is_classifier(cloned_estimator)` instead of `is_classifier(self.estimator)` for API consistency. Revision applied.

**Gate result**: ✅ PASSED - All 73 tests passed including `test_cv_generator_support`

**Trajectory**: Convergent success - FAIL_TO_PASS test now passes on first iteration

**Resolution**: The fix correctly prevents generator exhaustion by normalizing the cv parameter once at the start of `fit()`, matching the established pattern in RFECV.

## Audit: scikit-learn__scikit-learn-25973

### Patch verification
Patch is live in the container. Changes:
- Imports: Added `is_classifier` and `check_cv`
- In `fit()`: Normalize cv once before the loop: `cv = check_cv(self.cv, y, classifier=is_classifier(cloned_estimator))`
- Pass normalized `cv` through to `_get_best_new_feature_score`
- Use passed `cv` parameter in `cross_val_score` instead of `self.cv`

### Gate results
All 73 tests PASSED. Clean sweep.

### FAIL_TO_PASS
- `test_cv_generator_support`: **PASS** ✓

### PASS_TO_PASS regressions
None. All PASS_TO_PASS tests remain passing.

### Pre-existing failures
None observed in gate output.

### Analysis
The fix correctly addresses the generator exhaustion issue:
1. The cv generator is normalized once via `check_cv()` at the start of `fit()`, which wraps it in a splitter object that can be reused
2. The normalized cv is passed through the call chain instead of re-accessing `self.cv`
3. This prevents the generator from being consumed on the first iteration and exhausted for subsequent iterations

The implementation matches the established pattern in `RFECV` and other scikit-learn estimators that perform repeated cross-validation.

VERDICT: RESOLVED
RE-ENTER: none
