# Hypothesis graph: scikit-learn__scikit-learn-9288

## H₀: Test failure symptom (abduction)
The test `test_result_of_kmeans_equal_in_diff_n_jobs` fails because KMeans with n_jobs=1 produces different cluster labels than KMeans with n_jobs=2, even when using the same random_state=0. The assertion failure shows 78% of labels differ between the two runs.

## H₁: Root cause - RandomState mutation inconsistency (deduction)
**Confidence: 95% (deduction)** - traced through code, identified the exact difference in control flow.

The root cause is in `sklearn/cluster/k_means_.py` lines 363-398, in the `k_means` function's handling of the `n_init` loop:

**Sequential case (n_jobs=1, lines 363-378):**
- The same `random_state` object is passed to `kmeans_single` in all `n_init` iterations
- Each call to `kmeans_single` → `_init_centroids` → `_k_init` or `random_state.permutation` mutates the RandomState
- So iteration 1 uses random_state in state S₀, iteration 2 uses state S₁ (after mutation), etc.

**Parallel case (n_jobs>1, lines 380-398):**  
- Line 381: `seeds = random_state.randint(np.iinfo(np.int32).max, size=n_init)` generates n_init distinct integer seeds upfront
- Each parallel job receives a different integer seed and creates its own RandomState
- Each job's initialization is independent and deterministic

**Evidence:**
- `sklearn/cluster/k_means_.py:366-372` - sequential loop passes same random_state object to all iterations
- `sklearn/cluster/k_means_.py:381` - parallel case generates separate seeds before parallelization  
- `sklearn/cluster/k_means_.py:519` (`_kmeans_single_lloyd`) - calls `_init_centroids(... random_state=random_state, ...)`
- `sklearn/cluster/k_means_.py:721` (`_init_centroids`) - for 'k-means++', calls `_k_init` which mutates random_state
- `sklearn/cluster/k_means_.py:743` (`_init_centroids`) - for 'random', calls `random_state.permutation` which mutates random_state

## Edit site
`sklearn/cluster/k_means_.py` lines 363-378: The sequential case must generate separate seeds before the loop, matching the parallel case's behavior. Specifically:
1. Before the `for it in range(n_init):` loop, add: `seeds = random_state.randint(np.iinfo(np.int32).max, size=n_init)`
2. Inside the loop, change `random_state=random_state` to `random_state=seeds[it]` when calling `kmeans_single`

This ensures both code paths use the same seed generation strategy, making results deterministic and consistent regardless of n_jobs value.

## Gate Loop — Craft

### Iteration 1: Initial patch application

**Applied fix:**
- Modified `sklearn/cluster/k_means_.py` lines 363-373
- Added seed generation before sequential loop: `seeds = random_state.randint(np.iinfo(np.int32).max, size=n_init)`
- Changed sequential case to pass `random_state=seeds[it]` instead of `random_state=random_state`

**Gate result:** 3 failures (regression in unrelated functions)
- `test_k_means_explicit_init_shape[KMeans]`
- `test_k_means_explicit_init_shape[MiniBatchKMeans]`
- `test_sparse_mb_k_means_callable_init`

**Diagnosis:** Overly broad sed substitution replaced `random_state=random_state)` in the `_init_centroids` function (line 750) where `seeds[it]` is not in scope, causing `UnboundLocalError`.

### Iteration 2: Narrow the fix

**Revision:**
- Reverted line 750 in `_init_centroids` back to `random_state=random_state`
- Kept the intended fix at line 373 in the sequential k-means loop

**Gate result:** ✅ All 124 tests PASSED
- FAIL_TO_PASS test `test_result_of_kmeans_equal_in_diff_n_jobs` now passes
- No regressions

**Trajectory:** Oscillatory → Convergent (green)

**Resolution:** The fix correctly aligns sequential and parallel execution by using the same seed generation strategy in both branches. The sequential case now generates deterministic seeds upfront and passes individual seeds to each k-means run, matching the parallel behavior.

## Audit: scikit-learn__scikit-learn-9288

### Patch confirmation
```
 sklearn/cluster/k_means_.py | 3 ++-
 1 file changed, 2 insertions(+), 1 deletion(-)
```

**Applied diff:**
```diff
@@ -363,13 +363,14 @@ def k_means(X, n_clusters, sample_weight=None, init='k-means++',
     if effective_n_jobs(n_jobs) == 1:
         # For a single thread, less memory is needed if we just store one set
         # of the best results (as opposed to one set per run per thread).
+        seeds = random_state.randint(np.iinfo(np.int32).max, size=n_init)
         for it in range(n_init):
             # run a k-means once
             labels, inertia, centers, n_iter_ = kmeans_single(
                 X, sample_weight, n_clusters, max_iter=max_iter, init=init,
                 verbose=verbose, precompute_distances=precompute_distances,
                 tol=tol, x_squared_norms=x_squared_norms,
-                random_state=random_state)
+                random_state=seeds[it])
             # determine if these results are the best so far
             if best_inertia is None or inertia < best_inertia:
                 best_labels = labels.copy()
```

### Gate results

**FAIL_TO_PASS:**
- `sklearn/cluster/tests/test_k_means.py::test_result_of_kmeans_equal_in_diff_n_jobs`: ✅ PASSED

**PASS_TO_PASS regressions:** none

All 124 tests passed, no regressions observed.

**Pre-existing failures (not counted):** none

### Classification

The patch successfully resolves the issue:
- ✅ FAIL_TO_PASS test now passes
- ✅ All PASS_TO_PASS tests continue to pass (verified against baseline)
- ✅ No new failures introduced

The fix correctly synchronizes the seed generation strategy between single-threaded and multi-threaded execution paths by pre-generating independent seeds for each n_init iteration in the sequential case, matching the behavior already present in the parallel case.

VERDICT: RESOLVED
RE-ENTER: none

