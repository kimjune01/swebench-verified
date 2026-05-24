# Hypothesis graph: scikit-learn__scikit-learn-10297

## H₀: Initial diagnosis (abduction → deduction)

**Symptom**: Test fails with `TypeError: __init__() got an unexpected keyword argument 'store_cv_values'`

**Root cause**: RidgeClassifierCV.__init__() does not accept the `store_cv_values` parameter, even though:
1. The parent class _BaseRidgeCV.__init__() accepts it (sklearn/linear_model/ridge.py:1093)
2. The documentation mentions it (sklearn/linear_model/ridge.py:1310)
3. The sibling class RidgeCV works correctly because it inherits __init__ from _BaseRidgeCV

**Evidence**:
- sklearn/linear_model/ridge.py:1335-1336 — RidgeClassifierCV.__init__() signature lacks store_cv_values
- sklearn/linear_model/ridge.py:1337-1339 — super().__init__() call lacks store_cv_values parameter
- sklearn/linear_model/ridge.py:1093 — _BaseRidgeCV.__init__() accepts store_cv_values=False
- sklearn/linear_model/ridge.py:1128-1131 — _BaseRidgeCV.fit() handles store_cv_values correctly
- sklearn/linear_model/ridge.py:1374 — RidgeClassifierCV.fit() calls _BaseRidgeCV.fit(), so the logic is already there

**Confidence**: Deduction — 99%
The code path is clear: RidgeClassifierCV overrides __init__ without including store_cv_values, but the parent class already implements all the necessary logic.

**Edit sites**:
1. sklearn/linear_model/ridge.py:1335-1336 — Add store_cv_values=False to __init__ signature
2. sklearn/linear_model/ridge.py:1337-1339 — Pass store_cv_values to super().__init__()
3. sklearn/linear_model/ridge.py:1257-1300 — Add store_cv_values parameter to docstring Parameters section

**Status**: Active hypothesis

## Craft gate loop

### Iteration 1: Initial fix applied

**Hypothesis**: Thread `store_cv_values` parameter through `RidgeClassifierCV.__init__()` to parent `_BaseRidgeCV.__init__()`.

**Changes**:
1. Added `store_cv_values=False` parameter to `RidgeClassifierCV.__init__()` signature after `class_weight=None`
2. Passed `store_cv_values=store_cv_values` to `super().__init__()` call
3. Added parameter documentation to docstring matching RidgeCV's format

**Codex volley (pre-gate)**: Main fix confirmed correct. Codex noted missing cv_values_ attribute documentation, but verification showed it already exists in the Attributes section (lines 1302-1307).

**Gate result**: ✅ PASS
- All 29 tests passed
- `test_ridge_classifier_cv_store_cv_values` now passes
- No regressions

**Trajectory**: Convergent success — fix applied, test passes immediately.

**Resolution**: RESOLVED after 1 gate iteration. The parent class `_BaseRidgeCV` already implements full `store_cv_values` support; the parameter just needed to be threaded through the child class's constructor.

## Audit: Final verification

**Patch verification**: Confirmed live in tree — `store_cv_values` parameter added to `RidgeClassifierCV.__init__()` at line 1347.

### FAIL_TO_PASS results
- `sklearn/linear_model/tests/test_ridge.py::test_ridge_classifier_cv_store_cv_values`: **PASS** ✓

### PASS_TO_PASS regressions
None — all 28 PASS_TO_PASS tests remain passing.

### Pre-existing failures (not counted, confirmed against base capture)
- `test_dense_sparse`: XFAIL (expected failure, present in both baseline and current run)

### Baseline comparison
**Fail-on-base capture:**
- FAIL: `test_ridge_classifier_cv_store_cv_values` with `TypeError: __init__() got an unexpected keyword argument 'store_cv_values'`
- 28 other tests: PASS
- 1 test: XFAIL (test_dense_sparse)

**Current gate (with patch):**
- PASS: `test_ridge_classifier_cv_store_cv_values` 
- 28 other tests: PASS (no regressions)
- 1 test: XFAIL (test_dense_sparse, unchanged)

### Resolution
The fix successfully:
1. Adds `store_cv_values` parameter to constructor signature with default `False`
2. Passes parameter through to parent `_BaseRidgeCV` (which already has full implementation)
3. Documents the parameter in the class docstring
4. Resolves the failing test with zero regressions

**Contract satisfied**: All FAIL_TO_PASS pass ✓, zero PASS_TO_PASS regressions ✓

VERDICT: RESOLVED
RE-ENTER: none
