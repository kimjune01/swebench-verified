# Hypothesis graph: scikit-learn__scikit-learn-10908

## H1: get_feature_names missing _validate_vocabulary call (ACTIVE)
**Type**: abduction  
**Confidence**: 95% (deduction from code trace)

### Observation
Test `test_feature_names` fails with:
```
AttributeError: 'CountVectorizer' object has no attribute 'fixed_vocabulary_'
```
at line 547: `assert_false(cv.fixed_vocabulary_)`

### Root Cause
`get_feature_names()` does not call `_validate_vocabulary()` before checking vocabulary, unlike `transform()`.

**Evidence**:
- `sklearn/feature_extraction/text.py:994-997` - `get_feature_names()` directly calls `_check_vocabulary()` without ensuring `vocabulary_` exists
- `sklearn/feature_extraction/text.py:953-954` - `transform()` checks `if not hasattr(self, 'vocabulary_')` and calls `self._validate_vocabulary()` if needed
- `sklearn/feature_extraction/text.py:273-300` - `_validate_vocabulary()` sets both `self.vocabulary_` and `self.fixed_vocabulary_`

### Execution Flow
When `CountVectorizer(vocabulary=vocab)` is created:
1. `__init__` stores vocabulary in `self.vocabulary` (without underscore)
2. `self.vocabulary_` and `self.fixed_vocabulary_` are NOT set until `_validate_vocabulary()` is called
3. `transform()` calls `_validate_vocabulary()` on first use (line 953-954)
4. `get_feature_names()` does NOT call `_validate_vocabulary()`, goes directly to `_check_vocabulary()`
5. `_check_vocabulary()` expects `vocabulary_` to exist, raises NotFittedError

### Edit Site
`sklearn/feature_extraction/text.py` lines 994-997: Add vocabulary validation check before _check_vocabulary(), matching transform() pattern:

```python
def get_feature_names(self):
    """Array mapping from feature integer indices to feature name"""
    if not hasattr(self, 'vocabulary_'):
        self._validate_vocabulary()
    
    self._check_vocabulary()
    return [t for t, i in sorted(six.iteritems(self.vocabulary_),
                                 key=itemgetter(1))]
```

This ensures:
- When no vocabulary provided: `fixed_vocabulary_ = False` is set, then `_check_vocabulary()` raises ValueError as expected
- When vocabulary provided: `vocabulary_` and `fixed_vocabulary_ = True` are set, `get_feature_names()` works without calling fit()


## craft gate iteration 1

**Hypothesis**: Adding `if not hasattr(self, 'vocabulary_'): self._validate_vocabulary()` at the start of `get_feature_names()` will initialize the required attributes before use, mirroring the pattern in `transform()`.

**Implementation**: Modified `sklearn/feature_extraction/text.py` line 995 to add the vocabulary validation check before calling `_check_vocabulary()`.

**Gate result**: ✅ PASS - All 48 tests passed including `test_feature_names`

**Classification**: Convergent success - the fix directly addressed the root cause and all tests pass.

**Evidence**:
```
PASSED sklearn/feature_extraction/tests/test_text.py::test_feature_names
======================== 48 passed, 4 warnings in 0.84s ========================
```

**Resolution**: The fix correctly initializes `vocabulary_` and `fixed_vocabulary_` attributes before they are accessed, allowing:
1. Unfitted vectorizers to set `fixed_vocabulary_ = False` before raising ValueError
2. Vectorizers with custom vocabulary to work without calling fit()
3. All three test scenarios in `test_feature_names` to pass

---

# Audit: scikit-learn__scikit-learn-10908

## Patch confirmation
Patch is live: 3 insertions in `sklearn/feature_extraction/text.py`

```diff
+        if not hasattr(self, "vocabulary_"):
+            self._validate_vocabulary()
+
```

## FAIL_TO_PASS
- `sklearn/feature_extraction/tests/test_text.py::test_feature_names`: **PASS** ✅

## PASS_TO_PASS regressions
**None** - All 48 tests passed including all PASS_TO_PASS tests.

## Pre-existing failures (not counted)
**None** - `test_feature_names` was failing on base with `AttributeError: 'CountVectorizer' object has no attribute 'fixed_vocabulary_'` and is now passing.

## Full gate results
```
======================== 48 passed, 4 warnings in 0.82s ========================
```

All tests passed:
- FAIL_TO_PASS test now passes
- All PASS_TO_PASS tests remain passing
- No regressions introduced

VERDICT: RESOLVED
RE-ENTER: none
