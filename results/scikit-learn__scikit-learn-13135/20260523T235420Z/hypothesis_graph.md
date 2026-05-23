# Hypothesis graph: scikit-learn__scikit-learn-13135

## Hypothesis Node: Unsorted KMeans Centers

**Type**: Abduction → Deduction (confirmed by code reading)
**Confidence**: 99% (deduction)

### Observation
The test `test_nonuniform_strategies[kmeans-expected_2bins1-expected_3bins1-expected_5bins1]` fails with:
```
ValueError: bins must be monotonically increasing or decreasing
```
Raised by `np.digitize` at line 255 in `sklearn/preprocessing/_discretization.py`.

### Root Cause
In `_discretization.py:174`, the kmeans strategy extracts cluster centers from KMeans:
```python
centers = km.fit(column[:, None]).cluster_centers_[:, 0]
```

Then at line 175, it computes bin edges from consecutive pairs:
```python
bin_edges[jj] = (centers[1:] + centers[:-1]) * 0.5
```

**The bug**: KMeans.cluster_centers_ is ordered by cluster index (0, 1, 2, ...), NOT by center value. Computing midpoints between consecutive unsorted values produces non-monotonic bin edges.

### Evidence
Ran the failing example with n_bins=5:
- Input: `[0, 0.5, 2, 3, 9, 10]`
- Fitted centers: `[0.25, 3.0, 10.0, 2.0, 9.0]` (not sorted!)
- Computed bin_edges: `[0.0, 1.625, 6.5, 6.0, 5.5, 10.0]` (not monotonic: 6.5 > 6.0 > 5.5)

With sorted centers `[0.25, 2.0, 3.0, 9.0, 10.0]`:
- Computed bin_edges: `[0.0, 1.125, 2.5, 6.0, 9.5, 10.0]` (monotonic!)

### Why it sometimes passes
With n_bins=2 and n_bins=3, the unsorted centers happen to produce monotonic bin_edges by chance:
- n_bins=2: centers `[1.375, 9.5]` are sorted
- n_bins=3: centers `[2.5, 0.25, 9.5]` → bin_edges `[0.0, 1.375, 4.875, 10.0]` (lucky!)
- n_bins=5: centers `[0.25, 3.0, 10.0, 2.0, 9.0]` → bin_edges are non-monotonic

### Fix
Sort the centers at line 174 before computing bin edges:
```python
centers = np.sort(km.fit(column[:, None]).cluster_centers_[:, 0])
```

Or sort after extraction:
```python
centers = km.fit(column[:, None]).cluster_centers_[:, 0]
centers.sort()  # or centers = np.sort(centers)
```

### Edit Site
- `sklearn/preprocessing/_discretization.py` line 174: Add `np.sort()` around cluster_centers_ extraction or sort immediately after

### Historical Context
Introduced in commit 5a61af94e (Jul 2018) when kmeans strategy was added. The bug was present from the start—author assumed cluster_centers_ would be sorted.


## /craft gate loop

**Iteration 1 (gate run 1)**

**Hypothesis**: Recon diagnosis is correct — KMeans cluster centers need sorting before computing bin edges.

**Edit**: Applied one-line fix at `sklearn/preprocessing/_discretization.py:174`:
```python
centers = np.sort(km.fit(column[:, None]).cluster_centers_[:, 0])
```

**codex volley (pre-gate)**: Confirmed the fix is correct and scoped. No behavioral issues. Noted that duplicate centers could still cause issues but likely handled elsewhere.

**Gate outcome**: GREEN — all 34 tests passed, including FAIL_TO_PASS test `test_nonuniform_strategies[kmeans-expected_2bins1-expected_3bins1-expected_5bins1]`

**Evidence trajectory**: Convergent-success (first attempt, direct hit)

**Resolution**: The fix is complete. Sorting cluster centers ensures bin edges are monotonically increasing, satisfying np.digitize's precondition.

## /audit Verification

**Instance**: scikit-learn__scikit-learn-13135

**Patch Applied**:
```diff
diff --git a/sklearn/preprocessing/_discretization.py b/sklearn/preprocessing/_discretization.py
index dd969c12b..ca950771b 100644
--- a/sklearn/preprocessing/_discretization.py
+++ b/sklearn/preprocessing/_discretization.py
@@ -171,7 +171,7 @@ class KBinsDiscretizer(BaseEstimator, TransformerMixin):
 
                 # 1D k-means procedure
                 km = KMeans(n_clusters=n_bins[jj], init=init, n_init=1)
-                centers = km.fit(column[:, None]).cluster_centers_[:, 0]
+                centers = np.sort(km.fit(column[:, None]).cluster_centers_[:, 0])
                 bin_edges[jj] = (centers[1:] + centers[:-1]) * 0.5
                 bin_edges[jj] = np.r_[col_min, bin_edges[jj], col_max]
```

### FAIL_TO_PASS Results
- `test_nonuniform_strategies[kmeans-expected_2bins1-expected_3bins1-expected_5bins1]`: **PASSED** ✓

### PASS_TO_PASS Regressions
**None** — all 34 tests in the suite passed without regressions.

### Pre-existing Failures
**None** — the fail-on-base capture showed the same ValueError on the FAIL_TO_PASS test, confirming it was a genuine pre-patch failure.

### Gate Outcome
All 34 tests PASSED (100% pass rate):
- All FAIL_TO_PASS tests: ✓ PASS
- All PASS_TO_PASS tests: ✓ PASS  
- Zero regressions introduced
- Zero pre-existing failures affecting the contract

**VERDICT**: RESOLVED
**RE-ENTER**: none
