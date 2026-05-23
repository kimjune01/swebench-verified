# Hypothesis graph: scikit-learn__scikit-learn-13496

## H₀: Missing warm_start parameter exposure (abduction)
**Status**: Active
**Confidence**: 95% (deduction - directly traced from code)

### Observation
Test `test_iforest_warm_start` fails with:
```
TypeError: __init__() got an unexpected keyword argument 'warm_start'
```
at `sklearn/ensemble/tests/test_iforest.py:308`

### Root Cause
`IsolationForest.__init__()` (sklearn/ensemble/iforest.py:167-177) does not expose the `warm_start` parameter in its signature, even though:
1. Its parent class `BaseBagging.__init__()` (sklearn/ensemble/bagging.py:195-204) accepts `warm_start=False`
2. `BaseBagging` fully implements warm_start functionality (sklearn/ensemble/bagging.py:331-362)
3. The functionality works if `warm_start` is set after instantiation (per problem statement)

### Supporting Evidence
- `sklearn/ensemble/iforest.py:167-176` - IsolationForest.__init__ signature lacks warm_start parameter
- `sklearn/ensemble/bagging.py:200` - BaseBagging.__init__ defines warm_start=False parameter
- `sklearn/ensemble/bagging.py:213` - BaseBagging assigns self.warm_start = warm_start
- `sklearn/ensemble/bagging.py:338-362` - BaseBagging._fit uses warm_start to enable incremental tree addition
- `sklearn/ensemble/forest.py:1004` - RandomForestClassifier exposes warm_start (reference pattern)

### Edit Sites Required
1. **sklearn/ensemble/iforest.py:167-176** - Add `warm_start=False` to __init__ signature
2. **sklearn/ensemble/iforest.py:177-189** - Add `warm_start=warm_start` to super().__init__() call
3. **sklearn/ensemble/iforest.py:~120-125** - Add warm_start documentation to docstring (between verbose and behaviour parameters)

### Change Specification
**__init__ signature**: Add `warm_start=False` parameter after `verbose=0`
**super() call**: Add `warm_start=warm_start` argument to the parent initializer
**Docstring**: Add parameter documentation matching RandomForestClassifier pattern:
```
warm_start : bool, optional (default=False)
    When set to ``True``, reuse the solution of the previous call to fit
    and add more estimators to the ensemble, otherwise, just fit a whole
    new forest. See :term:`the Glossary <warm_start>`.
```

## /craft Gate Loop

### Iteration 1: Initial Fix

**Hypothesis**: `IsolationForest.__init__()` missing `warm_start` parameter exposure - add parameter to signature, pass to `BaseBagging`, and document.

**Edit sites applied**:
1. Added `warm_start : bool, optional (default=False)` documentation to docstring after `verbose` parameter (line 122-128)
2. Added `warm_start=False` parameter to `__init__` signature after `verbose=0` (line 177)
3. Added `warm_start=warm_start` to `super().__init__()` call after `verbose=verbose` (line 199)

**Codex pre-gate review**: "Nothing fundamentally wrong. Adding `warm_start` to `IsolationForest.__init__` and forwarding it to `BaseBagging.__init__` is the right fix. Append-only argument ordering is safe."

**Gate result**: ✓ PASS - All 20 tests passed, including `test_iforest_warm_start` (FAIL_TO_PASS)

**E-value**: Convergent - fixed the root cause on first attempt

**Status**: RESOLVED

## /audit Verification

### Phase 1: Patch verification
✓ Patch is live - warm_start parameter added to:
- Line 123-126: Documentation
- Line 184: __init__ signature
- Line 199: super().__init__() call

### Phase 2: Gate results
All 20 tests PASSED:
```
PASSED sklearn/ensemble/tests/test_iforest.py::test_iforest
PASSED sklearn/ensemble/tests/test_iforest.py::test_iforest_sparse
PASSED sklearn/ensemble/tests/test_iforest.py::test_iforest_error
PASSED sklearn/ensemble/tests/test_iforest.py::test_recalculate_max_depth
PASSED sklearn/ensemble/tests/test_iforest.py::test_max_samples_attribute
PASSED sklearn/ensemble/tests/test_iforest.py::test_iforest_parallel_regression
PASSED sklearn/ensemble/tests/test_iforest.py::test_iforest_performance
PASSED sklearn/ensemble/tests/test_iforest.py::test_iforest_works[0.25]
PASSED sklearn/ensemble/tests/test_iforest.py::test_iforest_works[auto]
PASSED sklearn/ensemble/tests/test_iforest.py::test_max_samples_consistency
PASSED sklearn/ensemble/tests/test_iforest.py::test_iforest_subsampled_features
PASSED sklearn/ensemble/tests/test_iforest.py::test_iforest_average_path_length
PASSED sklearn/ensemble/tests/test_iforest.py::test_score_samples
PASSED sklearn/ensemble/tests/test_iforest.py::test_iforest_warm_start
PASSED sklearn/ensemble/tests/test_iforest.py::test_deprecation
PASSED sklearn/ensemble/tests/test_iforest.py::test_behaviour_param
PASSED sklearn/ensemble/tests/test_iforest.py::test_iforest_chunks_works1[0.25-3]
PASSED sklearn/ensemble/tests/test_iforest.py::test_iforest_chunks_works1[auto-2]
PASSED sklearn/ensemble/tests/test_iforest.py::test_iforest_chunks_works2[0.25-3]
PASSED sklearn/ensemble/tests/test_iforest.py::test_iforest_chunks_works2[auto-2]
```

### Phase 3: Classification against baseline

**FAIL_TO_PASS**:
- `test_iforest_warm_start`: ✓ PASS (was failing with TypeError on base)

**PASS_TO_PASS** (19 tests):
- All 19 tests: ✓ PASS (no regressions)

**Pre-existing failures**: none

### Phase 4: Verdict
All FAIL_TO_PASS tests now pass. Zero regressions in PASS_TO_PASS tests. The fix correctly implements warm_start parameter exposure by adding it to the IsolationForest.__init__ signature and forwarding it to the BaseBagging parent class, enabling the already-implemented warm_start functionality in BaseBagging to work through the IsolationForest API.

