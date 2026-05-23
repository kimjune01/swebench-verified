# Hypothesis graph: scikit-learn__scikit-learn-13328

## Hypothesis H1 (recon iteration 1)
**Mode:** Deduction (traced code path, identified exact failure point)
**Confidence:** 98%

**Observation:** The test `test_huber_bool` fails with:
```
TypeError: The numpy boolean negative, the `-` operator, is not supported, use the `~` operator or the logical_not function instead.
```
at `sklearn/linear_model/huber.py:93` in `_huber_loss_and_gradient`:
```python
X_non_outliers = -axis0_safe_slice(X, ~outliers_mask, n_non_outliers)
```

**Root Cause:** 
When `HuberRegressor.fit()` is called with boolean X, the input validation at line 254 uses:
```python
X, y = check_X_y(X, y, copy=False, accept_sparse=['csr'], y_numeric=True)
```
This preserves boolean dtype (check_X_y defaults to dtype="numeric" which preserves non-object dtypes). The boolean X is then passed to `_huber_loss_and_gradient`, where line 93 attempts to apply the unary minus operator `-` to a boolean array slice, which numpy does not support.

**Evidence:**
- `sklearn/linear_model/huber.py:254` - check_X_y call without dtype parameter
- `sklearn/linear_model/huber.py:93` - unary minus on boolean array fails
- `sklearn/linear_model/base.py:126` - LinearRegression uses `dtype=FLOAT_DTYPES` in check_array
- `sklearn/utils/validation.py:29` - FLOAT_DTYPES = (np.float64, np.float32, np.float16)

**Fix specification:**
1. Add import: `from ..utils.validation import FLOAT_DTYPES` (after line 10)
2. Modify line 254 to include dtype parameter:
   ```python
   X, y = check_X_y(
       X, y, copy=False, accept_sparse=['csr'], y_numeric=True,
       dtype=FLOAT_DTYPES)
   ```

This ensures boolean (and other non-float) input is converted to float64 before processing, matching the behavior of other sklearn linear models.

**Edit sites:**
- `sklearn/linear_model/huber.py:10` - Add FLOAT_DTYPES import
- `sklearn/linear_model/huber.py:254` - Add dtype=FLOAT_DTYPES to check_X_y call

## Craft Gate Loop

### Iteration 1: Initial fix applied

**Changes:**
1. Added import: `from ..utils.validation import FLOAT_DTYPES` at line 12
2. Modified `check_X_y` call at line 254-256 to include `dtype=FLOAT_DTYPES`

**Codex pre-gate review:**
- Fix is directionally correct - coerces boolean input to float before `_huber_loss_and_gradient()` sees it
- Matches sklearn linear model patterns (e.g., LinearRegression)
- No obvious behavioral break for numeric input (int→float conversion is appropriate for this optimizer)

**Gate result:** ✅ PASS
- All 10 tests passed in test_huber.py
- `test_huber_bool` now passes (was failing with TypeError on boolean negation)
- No regressions in other Huber tests

**Resolution:** FAIL_TO_PASS test passing. Fix complete.


---

# Audit: scikit-learn__scikit-learn-13328

## FAIL_TO_PASS
- `sklearn/linear_model/tests/test_huber.py::test_huber_bool`: PASS ✓

## PASS_TO_PASS (9 tests, all passed)
- `test_huber_equals_lr_for_high_epsilon`: PASS ✓
- `test_huber_max_iter`: PASS ✓
- `test_huber_gradient`: PASS ✓
- `test_huber_sample_weights`: PASS ✓
- `test_huber_sparse`: PASS ✓
- `test_huber_scaling_invariant`: PASS ✓
- `test_huber_and_sgd_same_results`: PASS ✓
- `test_huber_warm_start`: PASS ✓
- `test_huber_better_r2_score`: PASS ✓

## PASS_TO_PASS regressions
None

## Pre-existing (not counted)
None

## Patch summary
Added `dtype=FLOAT_DTYPES` parameter to `check_X_y()` call in `HuberRegressor.fit()`. This forces conversion of boolean arrays to float before passing to the Huber loss function, preventing the TypeError that occurred when boolean dtype was propagated through to NumPy operations expecting numeric types.

