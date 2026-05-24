# Hypothesis graph: scikit-learn__scikit-learn-14087

## H₀: Initial diagnosis (abduction)

**Timestamp:** 2026-05-23
**Reasoning mode:** Deduction (traced code path, verified with minimal reproduction)
**Confidence:** 95-99%

### Observation
Tests fail with `TypeError: only integer scalar arrays can be converted to a scalar index` at `sklearn/linear_model/logistic.py:2184` when `LogisticRegressionCV` is called with `refit=False` and `penalty='l2'`.

### Root cause
In `LogisticRegressionCV.fit()`, the variable `l1_ratios_` is initialized as a Python list:
- Line 1971: `l1_ratios_ = self.l1_ratios` (for elasticnet)
- Line 1978: `l1_ratios_ = [None]` (for non-elasticnet penalties)

When `refit=False`, line 2184 attempts to index this list with a numpy array:
```python
best_indices_l1 = best_indices // len(self.Cs_)  # numpy array
self.l1_ratio_.append(np.mean(l1_ratios_[best_indices_l1]))  # FAILS
```

Python lists don't support fancy indexing with numpy arrays. The same `l1_ratios_` variable IS later converted to a numpy array at line 2199, but that's after the failing indexing operation.

In contrast, when `refit=True`, line 2144 uses scalar indexing which works fine with a list:
```python
l1_ratio_ = l1_ratios_[best_index_l1]  # scalar index, works with list
```

### Supporting evidence
- `sklearn/linear_model/logistic.py:1971-1978` — l1_ratios_ assigned as Python list
- `sklearn/linear_model/logistic.py:2184` — array indexing on list fails  
- `sklearn/linear_model/logistic.py:2199` — l1_ratios_ converted to numpy array (too late)
- Minimal reproduction confirms: `[None][np.array([0,0])]` raises TypeError, `np.asarray([None])[np.array([0,0])]` works

### Edit sites
- `sklearn/linear_model/logistic.py` lines 1978-1979: Immediately after `l1_ratios_ = [None]`, convert to numpy array with `l1_ratios_ = np.asarray(l1_ratios_)`
- OR `sklearn/linear_model/logistic.py` lines 1971-1979: Convert both branches (elasticnet and non-elasticnet) to numpy arrays


---

## Gate Loop (Craft)

### Iteration 1: Draft and volley

**Codex feedback on initial draft:**
- First draft tried to convert `l1_ratios_` to array but would still fail for non-elasticnet penalties
- When penalty is not 'elasticnet', `l1_ratios_` is `[None]`, and `np.mean(l1_ratios_[best_indices_l1])` would fail trying to take mean of None values
- Needed to add conditional logic in refit=False branch to handle non-elasticnet case

**Revised approach:**
1. Convert `l1_ratios_` to numpy array after assignment (enables fancy indexing)
2. In refit=False branch, add conditional: if elasticnet, compute mean; else append None

**Applied changes:**
- Line 1979: Added `l1_ratios_ = np.asarray(l1_ratios_)` after both assignment branches
- Lines 2185-2188: Replaced unconditional `self.l1_ratio_.append(np.mean(l1_ratios_[best_indices_l1]))` with:
  ```python
  if self.penalty == 'elasticnet':
      self.l1_ratio_.append(np.mean(l1_ratios_[best_indices_l1]))
  else:
      self.l1_ratio_.append(None)
  ```

**Gate result:** ✅ PASSED

All 175 tests passed, including:
- `test_LogisticRegressionCV_no_refit[ovr-l2]` ✅
- `test_LogisticRegressionCV_no_refit[multinomial-l2]` ✅
- `test_LogisticRegressionCV_no_refit[auto-l2]` ✅
- `test_LogisticRegressionCV_no_refit[ovr-elasticnet]` ✅
- `test_LogisticRegressionCV_no_refit[multinomial-elasticnet]` ✅
- `test_LogisticRegressionCV_no_refit[auto-elasticnet]` ✅

**Resolution:** The recon diagnosis was correct. The fix required two changes:
1. Convert `l1_ratios_` from Python list to numpy array to enable fancy indexing
2. Handle non-elasticnet penalties in refit=False branch by appending None instead of computing mean

Both elasticnet and non-elasticnet penalties now work correctly with refit=False.

---

## Audit: scikit-learn__scikit-learn-14087

**Timestamp:** 2026-05-23

### Patch status
✅ Patch is live: `sklearn/linear_model/logistic.py | 6 +++++-`

### FAIL_TO_PASS results
- test_LogisticRegressionCV_no_refit[ovr-l2]: **PASS** ✅
- test_LogisticRegressionCV_no_refit[multinomial-l2]: **PASS** ✅
- test_LogisticRegressionCV_no_refit[auto-l2]: **PASS** ✅

All 3 FAIL_TO_PASS tests now pass.

### PASS_TO_PASS regressions
**None** — all 175 tests passed with zero failures.

### Pre-existing failures (not counted, confirmed against base capture)
**None** — base capture showed all tests passing, gate shows all tests passing.

### Gate summary
- Total tests run: 175
- Passed: 175
- Failed: 0
- Warnings: 445
- Duration: 8.03s

VERDICT: RESOLVED
RE-ENTER: none
