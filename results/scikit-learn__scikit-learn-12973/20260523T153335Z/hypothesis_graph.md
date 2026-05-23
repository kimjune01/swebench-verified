# Hypothesis graph: scikit-learn__scikit-learn-12973

---
## Hypothesis Node: Initial Diagnosis (recon iteration 1)

**Timestamp:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")
**Mode:** deduction
**Confidence:** 99%

### Observation

Test `test_lasso_lars_fit_copyX_behaviour[False]` fails:
- Creates `LassoLarsIC()` with default `self.copy_X=True`
- Calls `fit(X, y, copy_X=False)` expecting X to be modified
- Assertion `assert copy_X == np.array_equal(X, X_copy)` fails
- Result: X was not modified despite `copy_X=False`

### Root Cause

`LassoLarsIC.fit()` uses `copy_X` inconsistently:
1. Line 1504: `_preprocess_data(..., self.copy_X)` — uses instance attribute (True)
2. Line 1510: `lars_path(..., copy_X=copy_X)` — uses method parameter (False)

When `fit(X, y, copy_X=False)` is called, `_preprocess_data` still receives `self.copy_X=True`, copying X before `lars_path` runs. The parameter to `fit()` is ignored for preprocessing.

### Edit Sites

- Line 1482: Change signature to `def fit(self, X, y, copy_X=None):`
- After line 1501: Add resolution logic: `copy_X = self.copy_X if copy_X is None else copy_X`
- Line 1504: Use resolved `copy_X` instead of `self.copy_X`

### Evidence

- `sklearn/linear_model/least_angle.py:1482` — fit signature with copy_X parameter
- `sklearn/linear_model/least_angle.py:1504` — uses self.copy_X
- `sklearn/linear_model/least_angle.py:1510` — uses copy_X parameter
- `sklearn/linear_model/base.py:93-130` — _preprocess_data copies when copy=True

## /craft gate loop

### Iteration 1 - Initial fix attempt
**Hypothesis**: Change `_preprocess_data` to use `copy_X` parameter instead of `self.copy_X`

**Change**: Modified line 1504 in `sklearn/linear_model/least_angle.py`:
```python
-            X, y, self.fit_intercept, self.normalize, self.copy_X)
+            X, y, self.fit_intercept, self.normalize, copy_X)
```

**Gate result**: Divergent (progress)
- FAIL_TO_PASS test `test_lasso_lars_fit_copyX_behaviour[False]` now PASSED ✓
- But PASS_TO_PASS test `test_lasso_lars_copyX_behaviour[False]` regressed

**Root cause of regression**: The two tests have different contracts:
- `test_lasso_lars_copyX_behaviour`: sets `copy_X` in `__init__`, expects it to be used when not overridden in `fit()`
- `test_lasso_lars_fit_copyX_behaviour`: passes `copy_X` to `fit()`, expects it to override `__init__` default

The fix always used the `fit()` parameter (defaulting to `True`), breaking the first contract.

### Iteration 2 - Parameter resolution with sentinel
**Hypothesis**: Use `None` as sentinel default for `copy_X` parameter in `fit()`, resolve to `self.copy_X` when not provided

**Changes**:
1. Modified `fit()` signature: `def fit(self, X, y, copy_X=None):`
2. Added resolution logic after `check_X_y`:
```python
if copy_X is None:
    copy_X = self.copy_X
```
3. Kept `_preprocess_data` using resolved `copy_X` value

**Codex review**: Confirmed this is the correct pattern. The `None` sentinel allows distinguishing:
- `fit(X, y)` → uses `self.copy_X`
- `fit(X, y, copy_X=False)` → uses explicit `False`

**Gate result**: Convergent (green) ✓
All 34 tests passed, including both:
- `test_lasso_lars_fit_copyX_behaviour[False]` (FAIL_TO_PASS) ✓
- `test_lasso_lars_copyX_behaviour[False]` (previously regressed) ✓

**Resolution**: RESOLVED - The fix correctly handles both use cases by properly resolving the `copy_X` parameter.

---

# Audit: scikit-learn__scikit-learn-12973

## FAIL_TO_PASS
- `sklearn/linear_model/tests/test_least_angle.py::test_lasso_lars_fit_copyX_behaviour[False]`: **PASS** ✓

## PASS_TO_PASS regressions
None — all 34 tests passed.

## Pre-existing (not counted)
None

## Patch Summary
The fix modified `LassoLarsIC.fit()` to:
1. Change `copy_X` parameter default from `True` to `None`
2. Resolve `copy_X` from `self.copy_X` when `None`
3. Pass resolved value to `_preprocess_data()` instead of always using `self.copy_X`

This allows callers to override the instance-level `copy_X` setting at fit time, which was the root cause of the failing test.

VERDICT: RESOLVED
RE-ENTER: none
