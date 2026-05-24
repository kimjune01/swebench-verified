# Hypothesis Graph: scikit-learn__scikit-learn-26194

## H₀: Initial observation (abduction)
The tests `test_roc_curve_drop_intermediate` and `test_roc_curve_with_probablity_estimates` fail because `roc_curve` returns thresholds > 1 when provided with probability estimates (scores in [0, 1]).

**Evidence:**
- `test_roc_curve_drop_intermediate`: Expected `[np.inf, 1.0, 0.7, 0.0]`, got `[2.0, 1.0, 0.7, 0.0]`
- `test_roc_curve_with_probablity_estimates[42]`: Expected first threshold to be `np.inf`, got `1.9699098521619942`

## H₁: Root cause identified (deduction - 99% confidence)
The root cause is at `sklearn/metrics/_ranking.py:1086`:
```python
thresholds = np.r_[thresholds[0] + 1, thresholds]
```

This line adds an extra threshold by computing `thresholds[0] + 1`, where `thresholds[0]` is the maximum score value. When `y_score` contains probability estimates (max ≤ 1), this produces values > 1, which is semantically incorrect for probabilities.

**Evidence:**
- Line 1086 is the only place where `thresholds[0] + 1` is computed
- The docstring at line 1022 documents this: "`thresholds[0]` represents no instances being predicted and is arbitrarily set to `max(y_score) + 1`"
- Verified with manual test:
  - Input: `y_score = [0.0, 0.2, 0.5, 0.6, 0.7, 1.0]` → `max(y_score) = 1.0`
  - Current output: `thresholds[0] = 2.0` (1.0 + 1)
  - Expected output: `thresholds[0] = np.inf`

**Fix:** Replace `thresholds[0] + 1` with `np.inf` to represent "no instances being predicted" in a way that makes sense for all score ranges, including probabilities.

## Edit sites identified (deduction - 99% confidence)
1. **Code fix** at `sklearn/metrics/_ranking.py:1086`:
   - Change: `thresholds = np.r_[thresholds[0] + 1, thresholds]`
   - To: `thresholds = np.r_[np.inf, thresholds]`

2. **Docstring fix** at `sklearn/metrics/_ranking.py:1022`:
   - Change: "is arbitrarily set to `max(y_score) + 1`"
   - To: "is arbitrarily set to `np.inf`"

3. **Example fix** at `sklearn/metrics/_ranking.py:1058`:
   - Change: `array([1.8 , 0.8 , 0.4 , 0.35, 0.1 ])`
   - To: `array([inf, 0.8 , 0.4 , 0.35, 0.1 ])`

## Craft gate loop — iteration 1

**Diagnosis:** Recon identified that `roc_curve` computes `thresholds[0] + 1` instead of using `np.inf`, causing threshold values > 1.0 for probability estimates.

**Edit sites applied:**
1. Line 1022: Updated docstring from "is arbitrarily set to \`max(y_score) + 1\`" to "is arbitrarily set to \`np.inf\`"
2. Line 1058: Updated doctest example from `array([1.8 , 0.8 , 0.4 , 0.35, 0.1 ])` to `array([ inf, 0.8 , 0.4 , 0.35, 0.1 ])` (with correct NumPy formatting)
3. Line 1086: Changed implementation from `thresholds = np.r_[thresholds[0] + 1, thresholds]` to `thresholds = np.r_[np.inf, thresholds]`

**codex volley (pre-gate):** Confirmed implementation correct; caught doctest formatting issue (space after `[` in array repr).

**Gate result:** PASSED — both FAIL_TO_PASS tests pass:
- `test_roc_curve_drop_intermediate`: PASSED
- `test_roc_curve_with_probablity_estimates[42]`: PASSED
- All 205 tests in test_ranking.py: PASSED

**Trajectory:** Convergent-success (first iteration)

---

# Audit: scikit-learn__scikit-learn-26194

## Patch verification

**Patch status:** Live (3 insertions, 3 deletions in `sklearn/metrics/_ranking.py`)

**Gate run:** 205 passed, 0 failed, 3 warnings (0.85s)

## FAIL_TO_PASS
- `sklearn/metrics/tests/test_ranking.py::test_roc_curve_drop_intermediate`: PASS ✓
- `sklearn/metrics/tests/test_ranking.py::test_roc_curve_with_probablity_estimates[42]`: PASS ✓

## PASS_TO_PASS regressions
None — all 205 tests in the suite passed.

## Pre-existing failures (not counted, confirmed against base capture)
None — baseline showed all tests passing.

## Patch summary

The fix changes `roc_curve` to use `np.inf` as the first threshold (representing "no instances being predicted") instead of computing `thresholds[0] + 1`. This resolves the issue where probability estimates (scores in [0, 1]) would produce semantically incorrect thresholds > 1.

**Changed:**
1. Implementation (line 1086): `thresholds = np.r_[np.inf, thresholds]`
2. Docstring (line 1022): Updated to document `np.inf` instead of `max(y_score) + 1`
3. Example (line 1058): Updated doctest output to show `inf` instead of `1.8`

VERDICT: RESOLVED
RE-ENTER: none
