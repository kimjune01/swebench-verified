# Hypothesis graph: scikit-learn__scikit-learn-12682

## H₀: Initial abduction (2026-05-22)

**Claim:** The test fails because `SparseCoder.__init__` does not accept the `transform_max_iter` parameter.

**Evidence:**
- Test error at `sklearn/decomposition/tests/test_dict_learning.py:97`: `TypeError: __init__() got an unexpected keyword argument 'transform_max_iter'`
- Test attempts to instantiate `SparseCoder` with `transform_max_iter=1` and `transform_max_iter=2000`

**Mode:** Abduction

**Status:** Active hypothesis

## H₁: Root cause (2026-05-22)

**Claim:** `SparseCoder` doesn't expose `max_iter` for the underlying `Lasso` estimator used in sparse encoding. The parameter chain is broken at three points: (1) `SparseCoder.__init__` doesn't accept `transform_max_iter`, (2) `_set_sparse_coding_params` doesn't handle it, and (3) `transform` doesn't pass it to `sparse_encode`.

**Evidence:**
- `sklearn/decomposition/dict_learning.py:995`: `SparseCoder.__init__` signature shows parameters: `dictionary`, `transform_algorithm`, `transform_n_nonzero_coefs`, `transform_alpha`, `split_sign`, `n_jobs`, `positive_code` — no `transform_max_iter`
- `sklearn/decomposition/dict_learning.py:864`: `_set_sparse_coding_params` signature shows no `max_iter` parameter
- `sklearn/decomposition/dict_learning.py:895`: `transform` method calls `sparse_encode` without passing `max_iter` argument
- `sklearn/decomposition/dict_learning.py:187`: `sparse_encode` function DOES accept `max_iter` parameter (default 1000)
- `sklearn/decomposition/dict_learning.py:151`: When `algorithm='lasso_cd'`, `Lasso` object is created with `max_iter=max_iter`

**Code path:**
1. `SparseCoder.__init__` calls `_set_sparse_coding_params` (line 995)
2. `SparseCoder.transform` (inherited from `SparseCodingMixin`) calls `sparse_encode` (line 895)
3. `sparse_encode` calls `_sparse_encode` with `max_iter` (line 321, 334)
4. `_sparse_encode` creates `Lasso(max_iter=max_iter)` when `algorithm='lasso_cd'` (line 151)

**Mode:** Deduction

**Confidence:** 98%

**Status:** Active hypothesis

## Edit sites

### Site 1: Add `transform_max_iter` parameter to `SparseCoder.__init__`
- **File:** `sklearn/decomposition/dict_learning.py`
- **Lines:** 993-1000 (the `__init__` signature and body)
- **Change:** Add `transform_max_iter=1000` parameter to signature, pass it to `_set_sparse_coding_params`

### Site 2: Add `max_iter` parameter to `_set_sparse_coding_params`
- **File:** `sklearn/decomposition/dict_learning.py`
- **Lines:** 864-876 (the method signature and body)
- **Change:** Add `max_iter=1000` parameter to signature, store as `self.transform_max_iter`

### Site 3: Pass `max_iter` to `sparse_encode` in `transform` method
- **File:** `sklearn/decomposition/dict_learning.py`
- **Lines:** 895-900 (the `sparse_encode` call)
- **Change:** Add `max_iter=self.transform_max_iter` to the `sparse_encode` call

### Site 4: Update `DictionaryLearning.__init__` for consistency
- **File:** `sklearn/decomposition/dict_learning.py`
- **Lines:** 1147-1159 (the `__init__` method)
- **Change:** Add `transform_max_iter=1000` parameter, pass to `_set_sparse_coding_params`

### Site 5: Update `MiniBatchDictionaryLearning.__init__` for consistency
- **File:** `sklearn/decomposition/dict_learning.py`
- **Lines:** 1336-1348 (the `__init__` method)
- **Change:** Add `transform_max_iter=1000` parameter, pass to `_set_sparse_coding_params`

## Notes

- Sites 4 and 5 are optional for the test to pass but recommended for API consistency across all classes using `SparseCodingMixin`
- The test specifically checks `SparseCoder` with `transform_algorithm='lasso_cd'`, which uses `Lasso` estimator
- Default value of 1000 matches the default in `sparse_encode` function

## Gate Loop — Iteration 1

**Patch applied:**
1. Added `transform_max_iter=1000` parameter to `_set_sparse_coding_params` (line 868)
2. Stored it as `self.transform_max_iter = transform_max_iter` (line 876)
3. Added pickle compatibility guard in `transform()`: `max_iter = getattr(self, "transform_max_iter", 1000)` (line 903)
4. Passed `max_iter=max_iter` to `sparse_encode` call in `transform()` (line 908)
5. Added `transform_max_iter=1000` parameter to `SparseCoder.__init__` (line 1000)
6. Passed `transform_max_iter` to `_set_sparse_coding_params` call (line 1005)

**codex volley:** Addressed naming (renamed from `max_iter` to `transform_max_iter` in helper method) and pickle compatibility (added getattr guard).

**Gate result:** ✅ PASS — All 67 tests passed including `test_max_iter`

**Trajectory:** Convergent success — test_max_iter now passes, `transform_max_iter=1` emits ConvergenceWarning as expected, `transform_max_iter=2000` converges without warnings.

**Resolution:** FAIL_TO_PASS test now passes, no regressions in PASS_TO_PASS tests.

## Audit — Final Verification (2026-05-22)

### Patch Status
Patch is live: `sklearn/decomposition/dict_learning.py` modified (14 insertions, 4 deletions)

### FAIL_TO_PASS Results
- `test_max_iter`: **PASSED** ✅
  - Was failing on base with: `TypeError: __init__() got an unexpected keyword argument 'transform_max_iter'`
  - Now passes: `SparseCoder` accepts `transform_max_iter` and propagates it correctly

### PASS_TO_PASS Results
All 67 tests passed, including all PASS_TO_PASS tests:
- `test_sparse_encode_shapes_omp`: PASSED ✅
- `test_dict_learning_shapes`: PASSED ✅
- `test_dict_learning_overcomplete`: PASSED ✅
- `test_dict_learning_lars_positive_parameter`: PASSED ✅
- All `test_dict_learning_positivity` variants: PASSED ✅
- All `test_minibatch_dictionary_learning_positivity` variants: PASSED ✅
- All other tests: PASSED ✅

**Regressions:** None

### Pre-existing Failures
None (all tests pass on patched version)

### Classification
- FAIL_TO_PASS coverage: 1/1 (100%)
- PASS_TO_PASS regressions: 0
- Total test suite: 67 passed, 1 warning (convergence warning in `test_sparse_coder_parallel_mmap` — expected, pre-existing)

### Verdict
**RESOLVED** — The patch successfully fixes the missing `transform_max_iter` parameter in `SparseCoder.__init__` without introducing any regressions. The parameter chain is now complete: `SparseCoder.__init__` → `_set_sparse_coding_params` → `transform()` → `sparse_encode()` → underlying `Lasso` estimator.
