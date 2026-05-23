# Hypothesis graph: scikit-learn__scikit-learn-13142

## H₀ (abduction): Symptom
When `n_init > 1` in GaussianMixture or BayesianGaussianMixture, `fit_predict(X)` and `predict(X)` return different labels with ~80-88% mismatch. Tests fail with assertion error comparing the two outputs.

**Evidence:**
- `sklearn/mixture/tests/test_gaussian_mixture.py::test_gaussian_mixture_fit_predict_n_init`: 815/1000 mismatched (81.5%)
- `sklearn/mixture/tests/test_bayesian_mixture.py::test_bayesian_mixture_fit_predict_n_init`: 878/1000 mismatched (87.8%)
- When `n_init=1` (or not specified), the tests pass - only fails when `n_init > 1`

## H₁ (deduction): Root cause - Final E-step uses wrong parameters

**Location:** `sklearn/mixture/base.py:262-274` in `fit_predict` method

**The bug:** The final E-step happens BEFORE setting the best parameters, causing labels to be computed with the wrong model state.

**Code flow with `n_init > 1`:**
1. Line 228: Loop through `n_init` initializations
2. Line 257: Save `best_params` when a better lower_bound is found
3. After loop completes, model state has parameters from the LAST initialization
4. Line 263: `_, log_resp = self._e_step(X)` - computes labels using LAST init's parameters
5. Line 272: `self._set_parameters(best_params)` - sets model to BEST init's parameters  
6. Line 274: `return log_resp.argmax(axis=1)` - returns labels from step 4

**Why it fails:**
- `fit_predict` returns labels computed with the last initialization's parameters
- `predict` (line 375) uses `self._estimate_weighted_log_prob(X).argmax(axis=1)` which depends on model parameters set in step 5
- When best initialization ≠ last initialization, they produce different labels

**Why existing test didn't catch it:**
- `test_gaussian_mixture_fit_predict` (line 580) doesn't specify `n_init`, so it defaults to 1
- When `n_init=1`, "last" and "best" are the same initialization, so bug doesn't manifest

**Historical context:**
- Commit `036dfdde2` (Nov 2018) added the final E-step to fix a different consistency issue
- The comment says it ensures consistency, but it was placed in the wrong order
- This commit introduced the current bug

**Confidence:** Deduction - 99%

**Supporting evidence:**
- `sklearn/mixture/base.py:263` - `_, log_resp = self._e_step(X)` before parameter setting
- `sklearn/mixture/base.py:272` - `self._set_parameters(best_params)` after E-step  
- `sklearn/mixture/base.py:375` - `predict` uses model parameters to compute labels

## craft gate-loop iteration 1

**Drafted fix:** Moved the final E-step computation (comment + `_, log_resp = self._e_step(X)` call) from before `self._set_parameters(best_params)` to after it. This ensures labels are computed using the best parameters, not the last initialization's parameters.

**codex pre-gate review:** Approved. Confirmed the fix addresses the root cause correctly. Noted no obvious breakage, warm-start behavior remains correct.

**Gate result:** ✅ GREEN - All 56 tests PASSED
- `sklearn/mixture/tests/test_bayesian_mixture.py::test_bayesian_mixture_fit_predict_n_init` PASSED
- `sklearn/mixture/tests/test_gaussian_mixture.py::test_gaussian_mixture_fit_predict_n_init` PASSED

**Evidence trajectory:** Convergent-resolved (first iteration success)

**Resolution:** The recon diagnosis was correct. Moving the E-step to after parameter restoration fixes the bug without breaking any existing tests.

---

# Audit: scikit-learn__scikit-learn-13142

## FAIL_TO_PASS
- sklearn/mixture/tests/test_bayesian_mixture.py::test_bayesian_mixture_fit_predict_n_init: **PASS** ✓
- sklearn/mixture/tests/test_gaussian_mixture.py::test_gaussian_mixture_fit_predict_n_init: **PASS** ✓

## PASS_TO_PASS regressions
None — all 56 tests passed.

## Pre-existing (not counted, confirmed against base capture)
None — no failures observed.

## Patch verification
The patch moves the final E-step from line 263 (before `_set_parameters(best_params)`) to line 276 (after parameter restoration). This ensures `fit_predict` computes labels using the best model parameters when `n_init > 1`, making it consistent with `predict`.

**Gate result:** 56 passed, 0 failed, 9 warnings in 5.36s

VERDICT: RESOLVED
RE-ENTER: none
