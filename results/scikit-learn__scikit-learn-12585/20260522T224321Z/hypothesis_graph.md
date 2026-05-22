# Hypothesis graph: scikit-learn__scikit-learn-12585

## H₀: Baseline observation (abduction)
The test `test_clone_estimator_types` fails because when `clone()` recursively tries to clone a parameter that is a class type (not an instance), it attempts to call `get_params(deep=False)` on the class itself, which fails with "TypeError: get_params() missing 1 required positional argument: 'self'".

**Evidence:**
- Test creates: `clf = MyEstimator(empty=MyEstimator)` where `MyEstimator` is a class
- `clone(clf)` recursively calls `clone(MyEstimator, safe=False)` for the parameter
- At `sklearn/base.py:60`, `estimator.get_params(deep=False)` is called on the class
- Instance method `get_params()` requires `self`, but when called on a class (not instance), `self` is not automatically provided

## H₁: Root cause - missing type check in clone (deduction)
The condition at `sklearn/base.py:51` checks `not hasattr(estimator, 'get_params')` to determine if an object is an estimator. However, this check returns False for both estimator *instances* AND estimator *classes*, because both have the `get_params` method defined. When the parameter is a class, the code proceeds to line 60 and tries to call an unbound instance method, causing a TypeError.

**Confidence: 98% (deduction)**

**Supporting evidence:**
- `sklearn/base.py:51` - condition: `elif not hasattr(estimator, 'get_params'):`
- `sklearn/base.py:60` - failure site: `new_object_params = estimator.get_params(deep=False)`
- Verified: `hasattr(MyEstimator, 'get_params')` returns True (class has the method)
- Verified: `isinstance(MyEstimator, type)` returns True (it's a class)
- Verified: `isinstance(MyEstimator(), type)` returns False (instance is not a type)
- Verified: `copy.deepcopy(MyEstimator) is MyEstimator` returns True (preserves identity)

**Fix specification:**
Change line 51 to: `elif not hasattr(estimator, 'get_params') or isinstance(estimator, type):`

This additional check catches class types and routes them to the deepcopy path (when safe=False), which preserves class identity as required by the test assertion `clf.empty is clf2.empty`.


## craft gate loop

### Iteration 1: Initial fix

**Change**: Modified `sklearn/base.py` line 51 to add `isinstance(estimator, six.class_types)` check to route class types to the deepcopy branch.

**Diff**:
```diff
--- a/sklearn/base.py
+++ b/sklearn/base.py
@@ -48,7 +48,7 @@ def clone(estimator, safe=True):
     # XXX: not handling dictionaries
     if estimator_type in (list, tuple, set, frozenset):
         return estimator_type([clone(e, safe=safe) for e in estimator])
-    elif not hasattr(estimator, 'get_params'):
+    elif not hasattr(estimator, 'get_params') or isinstance(estimator, six.class_types):
         if not safe:
             return copy.deepcopy(estimator)
         else:
```

**Codex review**: Approved the approach but recommended using `six.class_types` instead of plain `type` for Python 2/3 compatibility. This was incorporated.

**Gate result**: ✅ PASS — All 23 tests passed including `test_clone_estimator_types`. The fix correctly routes class types (like `MyEstimator` class itself) to the deepcopy branch when `safe=False`, which preserves class identity as required by the test assertion `clf.empty is clf2.empty`.

**Trajectory**: Convergent-success — FAIL_TO_PASS test now passes on first iteration.

## Audit: scikit-learn__scikit-learn-12585

**Patch confirmed live**: 1 file changed (sklearn/base.py)

### Gate results

All 23 tests **PASSED**.

### FAIL_TO_PASS
- `test_clone_estimator_types`: **PASS** ✓

### PASS_TO_PASS regressions
None. All 22 PASS_TO_PASS tests remain passing.

### Pre-existing failures (not counted, confirmed against base capture)
None. The only failure on base was `test_clone_estimator_types`, which is now fixed.

### Kill report
N/A — patch is RESOLVED.

VERDICT: RESOLVED
RE-ENTER: none
