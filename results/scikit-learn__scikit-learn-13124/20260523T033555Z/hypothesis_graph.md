# Hypothesis graph: scikit-learn__scikit-learn-13124

## H0: Initial Hypothesis (Abduction)
**Status**: Confirmed via code analysis and simulation
**Timestamp**: 2026-05-22 Recon Phase

The tests fail because `StratifiedKFold` with `shuffle=True` produces identical test folds regardless of `random_state` value. When sorted, different random_state values produce the same fold pairs (e.g., `[(0, 5), (1, 6), (2, 7), (3, 8), (4, 9)]`).

### Failure Mode
The test `test_shuffle_stratifiedkfold` asserts that two `StratifiedKFold` objects with different `random_state` values should produce different test fold compositions. However:
- With `random_state=0`: test folds in original order `[(0,5), (1,6), (2,7), (3,8), (4,9)]`  
- With `random_state=1`: test folds in different order but when sorted: `[(0,5), (1,6), (2,7), (3,8), (4,9)]` (identical!)

### Root Cause (Deduction - 95% confidence)
**Location**: `sklearn/model_selection/_split.py:623` in `StratifiedKFold._make_test_folds()`

**The Bug**:
```python
def _make_test_folds(self, X, y=None):
    rng = self.random_state  # Line 623 - WRONG: just assigns integer
    ...
    per_cls_cvs = [
        KFold(self.n_splits, shuffle=self.shuffle,
              random_state=rng).split(np.zeros(max(count, self.n_splits)))
        for count in y_counts]
```

When `self.random_state` is an integer (e.g., `random_state=0`), all KFold objects receive the same integer. Later, when each KFold runs `_iter_test_indices()`, it calls:
```python
check_random_state(self.random_state).shuffle(indices)
```

Since `self.random_state` is an integer, `check_random_state()` creates a **new** `RandomState` object with that seed **each time**. Result: all classes get identical shuffle patterns.

**Evidence**:
- `KFold._iter_test_indices` (lines 433-434): `if self.shuffle: check_random_state(self.random_state).shuffle(indices)`
- Simulation confirms: two KFold objects with `random_state=0` produce identical shuffles `[2,0,1,3,4]`
- Simulation with fix: two KFold objects sharing a RandomState *object* produce different shuffles

**The Fix**:
Change line 623 from:
```python
rng = self.random_state
```
to:
```python
rng = check_random_state(self.random_state)
```

This converts the integer to a RandomState object once. When the same RandomState object is passed to multiple KFold objects, they share the same stateful RNG, and each shuffle advances the state, producing different patterns for each class.

### Supporting Evidence
- `sklearn/model_selection/_split.py:9`: `check_random_state` is already imported
- Simulation shows fix works: `random_state=0` produces `[(0,7), (1,6), (2,5), (3,9), (4,8)]`, `random_state=1` produces `[(0,8), (1,7), (2,5), (3,6), (4,9)]` (different!)
- No other code paths modify test fold assignment

### Edit Sites
- `sklearn/model_selection/_split.py` line 623: Change `rng = self.random_state` to `rng = check_random_state(self.random_state)`


## Craft gate-loop

### Iteration 1: Draft and volley

**Drafted fix:** Changed line 623 from `rng = self.random_state` to `rng = check_random_state(self.random_state)`

**Codex feedback:** Fix should be conditional. When `shuffle=False`, calling `check_random_state` may break non-shuffled stratified CV behavior. Proposed: `rng = check_random_state(self.random_state) if self.shuffle else self.random_state`

**Revised fix:** Applied conditional version as suggested by codex.

### Iteration 1: Gate result

**Status:** ✓ PASSED

All 61 tests passed including the target test `test_shuffle_stratifiedkfold`.

**Trajectory:** Convergent-resolved — first gate run passed after incorporating codex's structural catch.

**Resolution:** The conditional fix correctly addresses the root cause by sharing a stateful RandomState object across per-class KFold splitters only when shuffling, while preserving existing behavior for non-shuffled splits.

## Audit: scikit-learn__scikit-learn-13124

### FAIL_TO_PASS
- `test_shuffle_stratifiedkfold`: **PASSED** ✓

### PASS_TO_PASS regressions
None — all 61 tests passed.

### Pre-existing failures (not counted)
None observed in this audit run.

### Classification
The patch successfully resolved the issue:
1. The target test `test_shuffle_stratifiedkfold` now passes (was failing on base)
2. All 61 tests in the suite pass with zero regressions
3. The fix is minimal and surgical: conditional `check_random_state()` only when `shuffle=True`

**Patch summary:**
```python
# Line 623 in sklearn/model_selection/_split.py
- rng = self.random_state
+ rng = check_random_state(self.random_state) if self.shuffle else self.random_state
```

This ensures that when shuffling, a stateful RandomState object is shared across per-class KFold splitters, producing different shuffle patterns for each class. When not shuffling, the original behavior is preserved.

VERDICT: RESOLVED
RE-ENTER: none
