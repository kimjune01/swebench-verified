# Hypothesis graph: scikit-learn__scikit-learn-14496

## Hypothesis H1: Float min_samples not converted to int before NearestNeighbors
**Type**: Abduction (from symptom trace)
**Status**: Active
**Confidence**: 95% (deduction from code reading)

### Symptom
Test `test_extract_xi` fails with:
```
TypeError: n_neighbors does not take <class 'float'> value, enter integer value
```
at `sklearn/neighbors/base.py:276` when NearestNeighbors is instantiated.

### Root Cause
In `sklearn/cluster/optics_.py`:
- **Line 439-440** in `compute_optics_graph()`:
  ```python
  if min_samples <= 1:
      min_samples = max(2, min_samples * n_samples)
  ```
  When `min_samples` is a float (e.g., 0.1), this computes `0.1 * n_samples` which produces a float.
  
- **Line 448**: This float value is passed to `NearestNeighbors`:
  ```python
  nbrs = NearestNeighbors(n_neighbors=min_samples, ...)
  ```
  
- `NearestNeighbors` validates that `n_neighbors` is an integer at `sklearn/neighbors/base.py:273-276`, raising TypeError for float values.

### Secondary Issue
The same bug exists for `min_cluster_size` in `cluster_optics_xi()`:
- **Lines 626-627**:
  ```python
  if min_cluster_size <= 1:
      min_cluster_size = max(2, min_cluster_size * n_samples)
  ```
  This also produces a float but is used in comparisons (line 873) which work with floats, so it's less critical but still semantically wrong.

### Edit Sites
1. `sklearn/cluster/optics_.py:440` - Convert min_samples to int after multiplication
2. `sklearn/cluster/optics_.py:627` - Convert min_cluster_size to int after multiplication

### Evidence
- Test added: `OPTICS(min_samples=0.1, min_cluster_size=0.08, ...)`
- Stack trace confirms error at NearestNeighbors instantiation
- Code inspection confirms float is passed without conversion

## Gate Loop (Craft)

### Iteration 1: Codex volley + apply

**Drafted fix**: Added `int(round(...))` wrapping around the three edit sites per recon handoff.

**Codex feedback**: `round()` is wrong — it changes behavior and uses banker's rounding. The correct fix is `int(min_samples * n_samples)` (truncation), not `int(round(...))`. Current upstream sklearn already uses `int()` without `round()`.

**Revised fix**: Changed to `int()` without `round()` at all three locations:
- Line 440: `min_samples = max(2, int(min_samples * n_samples))`
- Line 622: `min_samples = max(2, int(min_samples * n_samples))`  
- Line 627: `min_cluster_size = max(2, int(min_cluster_size * n_samples))`

**Gate result**: GREEN — all 40 tests passed, including `test_extract_xi`.

**Evidence trajectory**: Divergent (progress) — test went from TypeError to passing.

**Resolution**: RESOLVED

---

# Audit: scikit-learn__scikit-learn-14496

## FAIL_TO_PASS
- `sklearn/cluster/tests/test_optics.py::test_extract_xi`: **PASS** ✓

## PASS_TO_PASS regressions
None — all 40 tests passed with no regressions.

## Pre-existing (not counted, confirmed against base capture)
None — the fail-on-base capture showed a pre-existing TypeError in `sklearn/neighbors/base.py:276` unrelated to the OPTICS test suite.

## Summary
The patch wraps three sites with `int()` to convert fractional `min_samples` and `min_cluster_size` values to integers before passing to `NearestNeighbors`:

1. Line 440: `min_samples = max(2, int(min_samples * n_samples))`
2. Line 622: `min_samples = max(2, int(min_samples * n_samples))`
3. Line 627: `min_cluster_size = max(2, int(min_cluster_size * n_samples))`

Gate output:
- 40 tests collected
- 40 passed
- 0 failed
- 1 warning (unrelated)
- Test time: 2.61s

VERDICT: RESOLVED
RE-ENTER: none
