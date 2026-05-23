# Hypothesis graph: scikit-learn__scikit-learn-25232

## Hypothesis Node: H0 (Initial Diagnosis)

**Failure Mode**: TypeError - `__init__() got an unexpected keyword argument 'fill_value'`

**Root Cause**: `IterativeImputer` class does not accept a `fill_value` parameter in its `__init__()` method, even though:
1. The documentation for `keep_empty_features` parameter (line 177) references `fill_value`
2. The internal `SimpleImputer` (used for initial imputation) already supports `fill_value`
3. The issue requests this feature to allow custom constant values when `initial_strategy="constant"`

**Evidence**:
- `sklearn/impute/_iterative.py:301-320` - `__init__()` has no `fill_value` parameter
- `sklearn/impute/_iterative.py:613-617` - `SimpleImputer` is created without passing `fill_value`
- `sklearn/impute/_base.py:~145-155` - `SimpleImputer.__init__()` accepts `fill_value=None`
- `sklearn/impute/tests/test_impute.py:test_iterative_imputer_constant_fill_value` - Test expects `fill_value=100` to propagate to `initial_imputer_.statistics_`

**Confidence**: Deduction - 99%

**Edit Sites Required**:
1. `sklearn/impute/_iterative.py:~130-140` - Add `fill_value` parameter documentation
2. `sklearn/impute/_iterative.py:~277-293` - Add `fill_value` to `_parameter_constraints` dict with `"no_validation"`
3. `sklearn/impute/_iterative.py:301-320` - Add `fill_value=None` parameter to `__init__()`
4. `sklearn/impute/_iterative.py:~301-320` - Add `self.fill_value = fill_value` in `__init__()` body
5. `sklearn/impute/_iterative.py:613-617` - Pass `fill_value=self.fill_value` when creating `SimpleImputer`


## Craft gate-loop: iteration 1

**Hypothesis**: Add `fill_value` parameter to `IterativeImputer` and pass it through to `SimpleImputer`

**Edit sites applied**:
1. Added `fill_value` parameter documentation after `initial_strategy` parameter (line ~120)
2. Added `"fill_value": "no_validation"` to `_parameter_constraints` dict (line 289)
3. Added `fill_value=None` to `__init__` signature after `initial_strategy` (line 310)
4. Added `self.fill_value = fill_value` assignment in `__init__` body after `self.initial_strategy` (line 332)
5. Added `fill_value=self.fill_value` to `SimpleImputer` instantiation (line 624)

**Gate result**: ✅ PASSED — All 217 tests passed, including `test_iterative_imputer_constant_fill_value`

**Trajectory**: Convergent (resolved) — The minimal parameter passthrough fixed the issue exactly as recon predicted.

## Audit: scikit-learn__scikit-learn-25232

### FAIL_TO_PASS
- `sklearn/impute/tests/test_impute.py::test_iterative_imputer_constant_fill_value`: **PASS**

### PASS_TO_PASS regressions
None

### Pre-existing (not counted, confirmed against base capture)
None

### Verification
- Patch live: 9 lines added to `sklearn/impute/_iterative.py`
- Gate: 217 tests passed, 211 warnings, 0 failures
- Full contract met: FAIL_TO_PASS passes, no PASS_TO_PASS regressions

The fix correctly adds `fill_value` parameter to `IterativeImputer.__init__()` and passes it through to the internal `SimpleImputer`, enabling custom constant values for initial imputation when `initial_strategy="constant"`.

VERDICT: RESOLVED
RE-ENTER: none
