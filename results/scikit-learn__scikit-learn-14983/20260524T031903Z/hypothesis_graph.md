# Hypothesis graph: scikit-learn__scikit-learn-14983

## Hypothesis H0 (abduction, 85%)

**Observation**: Tests fail because `repr(RepeatedKFold())` returns `'<sklearn.model_selection._split.RepeatedKFold object at 0x...>'` instead of `'RepeatedKFold(n_repeats=10, n_splits=5, random_state=None)'`.

**Root cause**: 
1. `_RepeatedSplits` class (parent of both `RepeatedKFold` and `RepeatedStratifiedKFold`) does not have a `__repr__` method
2. `_RepeatedSplits` does not inherit from `BaseCrossValidator` (which provides `__repr__` via `_build_repr`)
3. `RepeatedKFold` and `RepeatedStratifiedKFold` do not store `n_splits` as an instance attribute (only in `self.cvargs`)

**Evidence**:
- `sklearn/model_selection/_split.py:1066` - `_RepeatedSplits` uses `metaclass=ABCMeta` but doesn't inherit from `BaseCrossValidator`
- `sklearn/model_selection/_split.py:105` - `BaseCrossValidator.__repr__` uses `_build_repr(self)`
- `sklearn/model_selection/_split.py:1102-1104` - Parent `_RepeatedSplits.__init__` stores `self.n_repeats` and `self.random_state` but `n_splits` goes into `self.cvargs`
- `sklearn/model_selection/_split.py:1217` - `RepeatedKFold.__init__` doesn't store `self.n_splits`
- Confirmed via test: `getattr(RepeatedKFold(n_splits=2), 'n_splits', 'NOT FOUND')` returns `'NOT FOUND'`

**Required changes**:
1. Add `__repr__` method to `_RepeatedSplits` class that calls `_build_repr(self)`
2. Store `self.n_splits = n_splits` in `RepeatedKFold.__init__` before calling `super().__init__()`
3. Store `self.n_splits = n_splits` in `RepeatedStratifiedKFold.__init__` before calling `super().__init__()`

**Confidence**: Abduction - 85% (pattern is clear from other classes, but haven't tested the fix)


## craft gate-loop node 1

**Action**: Applied fix based on recon diagnosis:
1. Added `__repr__` method to `_RepeatedSplits` class that returns `_build_repr(self)`
2. Stored `self.n_splits = n_splits` in `RepeatedKFold.__init__` after `super().__init__()`
3. Stored `self.n_splits = n_splits` in `RepeatedStratifiedKFold.__init__` after `super().__init__()`

**codex volley**: Approved with note about attribute placement after super() for better validation ordering. Noted duplicated state is acceptable (sklearn pattern). No obvious breakage.

**Gate result**: ✅ GREEN
- All 107 tests passed
- FAIL_TO_PASS tests now passing:
  - `test_repeated_cv_repr[RepeatedKFold]`
  - `test_repeated_cv_repr[RepeatedStratifiedKFold]`

**Trajectory**: Convergent success (first iteration)

**Resolution**: FAIL_TO_PASS requirements met. Fix complete.


## Audit node: scikit-learn__scikit-learn-14983

**Patch verification**: 5 lines added to `sklearn/model_selection/_split.py`
- Added `__repr__` method to `_RepeatedSplits` base class
- Added `self.n_splits = n_splits` to `RepeatedKFold.__init__`
- Added `self.n_splits = n_splits` to `RepeatedStratifiedKFold.__init__`

**Gate execution**: All 107 tests passed

### FAIL_TO_PASS results
- `test_repeated_cv_repr[RepeatedKFold]`: PASS ✅
- `test_repeated_cv_repr[RepeatedStratifiedKFold]`: PASS ✅

### PASS_TO_PASS regressions
None — all 107 tests passed with no failures.

### Pre-existing failures (confirmed against base capture)
None — baseline had 2 failures (the FAIL_TO_PASS tests), both now resolved.

**Verdict**: RESOLVED — All FAIL_TO_PASS tests now pass with zero regressions.

**Route**: No re-entry needed.
