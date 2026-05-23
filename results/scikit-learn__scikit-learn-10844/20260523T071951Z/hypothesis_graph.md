# Hypothesis graph: scikit-learn__scikit-learn-10844

## H₀: Initial observation (abduction)
**Node type**: abduction  
**Confidence**: 60%  
**Status**: superseded by H₁

The test `test_int_overflow_mutual_info_fowlkes_mallows_score` fails because `fowlkes_mallows_score` returns NaN instead of a finite float value when pk and qk are large integers whose product overflows int64.

## H₁: Root cause localized (deduction)
**Node type**: deduction  
**Confidence**: 99%  
**Status**: active

**Root cause**: Line 859 of `sklearn/metrics/cluster/supervised.py` computes `tk / np.sqrt(pk * qk)` where pk and qk are large integers. When `pk * qk` exceeds the int64 range (2^63 - 1), integer overflow occurs, producing a negative value. Taking the square root of this negative value yields NaN.

**Evidence**:
- Test case values: pk=5152663196, qk=3294371982
- Product: pk * qk overflows to -1471954808124577144 (should be ~1.697e19)
- Result: np.sqrt(negative_value) = nan
- Proposed fix: `np.sqrt(tk / pk) * np.sqrt(tk / qk)` avoids the intermediate multiplication
- Mathematically equivalent: sqrt(tk/pk) * sqrt(tk/qk) = sqrt(tk²/(pk*qk)) = tk/sqrt(pk*qk) for tk >= 0

**Supporting code**:
- `sklearn/metrics/cluster/supervised.py:856-859`:
  ```python
  tk = np.dot(c.data, c.data) - n_samples
  pk = np.sum(np.asarray(c.sum(axis=0)).ravel() ** 2) - n_samples
  qk = np.sum(np.asarray(c.sum(axis=1)).ravel() ** 2) - n_samples
  return tk / np.sqrt(pk * qk) if tk != 0. else 0.
  ```

**Edit site**: `sklearn/metrics/cluster/supervised.py` line 859
- Change: `return tk / np.sqrt(pk * qk) if tk != 0. else 0.`
- To: `return np.sqrt(tk / pk) * np.sqrt(tk / qk) if tk != 0. else 0.`
- Rationale: Avoids integer overflow by dividing before multiplying under the square root

**Related context**: Git history shows recent fix for similar issue in `mutual_info_score` (commit 4a2b96f8e), indicating maintainers are aware of overflow risks in this file.

## Craft gate loop

**Iteration 1**: PASS

Applied fixes:
1. `mutual_info_score` (line 604-605): Replaced `outer = pi.take(nzx).astype(np.int64) * pj.take(nzy).astype(np.int64); log_outer = -np.log(outer) + ...` with `log_outer = -np.log(pi.take(nzx)) - np.log(pj.take(nzy)) + ...` to avoid int64 overflow by computing in log space.

2. `fowlkes_mallows_score` (line 859): Replaced `tk / np.sqrt(pk * qk)` with `np.sqrt(tk / float(pk)) * np.sqrt(tk / float(qk))` to avoid int64 overflow in `pk * qk` multiplication and ensure float division for Python 2 compatibility.

Gate result: All 17 tests passed, including `test_int_overflow_mutual_info_fowlkes_mallows_score`.

## Audit: scikit-learn__scikit-learn-10844

### Patch verification
- Patch live: ✓ (1 file changed, 3 insertions(+), 3 deletions(-))
- Gate run: Complete (17 tests collected)

### FAIL_TO_PASS
- `test_int_overflow_mutual_info_fowlkes_mallows_score`: **PASS** ✓

### PASS_TO_PASS regressions
None - all 16 PASS_TO_PASS tests passed:
- test_error_messages_on_wrong_input: PASS
- test_perfect_matches: PASS
- test_homogeneous_but_not_complete_labeling: PASS
- test_complete_but_not_homogeneous_labeling: PASS
- test_not_complete_and_not_homogeneous_labeling: PASS
- test_non_consicutive_labels: PASS
- test_adjustment_for_chance: PASS
- test_adjusted_mutual_info_score: PASS
- test_expected_mutual_info_overflow: PASS
- test_entropy: PASS
- test_contingency_matrix: PASS
- test_contingency_matrix_sparse: PASS
- test_exactly_zero_info_score: PASS
- test_v_measure_and_mutual_information: PASS
- test_fowlkes_mallows_score: PASS
- test_fowlkes_mallows_score_properties: PASS

### Pre-existing failures
None - the fail-on-base capture showed only `test_int_overflow_mutual_info_fowlkes_mallows_score` failing (expected, as it's in FAIL_TO_PASS).

### Summary
The craft patch successfully fixed both overflow issues:
1. `mutual_info_score`: Avoided int64 overflow by computing in log space
2. `fowlkes_mallows_score`: Avoided int64 overflow by refactoring `tk / sqrt(pk * qk)` → `sqrt(tk/pk) * sqrt(tk/qk)`

All FAIL_TO_PASS tests now pass, zero regressions introduced.

VERDICT: RESOLVED
RE-ENTER: none
