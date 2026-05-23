# Hypothesis graph: matplotlib__matplotlib-26113

## H₀: Initial Observation (abduction)
The test `test_hexbin_mincnt_behavior_upon_C_parameter` fails because hexbin produces different output when C parameter is provided vs not provided, even with the same mincnt=1 setting.

Test data: 4 points at positions (0,0), (0,0), (6,0), (0,6) - i.e., one bin with 2 points and two bins with 1 point each.

Observed behavior:
- Without C, mincnt=1: shows 3 hexbins (correct)
- With C, mincnt=1: shows only 1 hexbin (incorrect - should show 3)

## H₁: Root Cause Identified (deduction - 99%)

**Location**: `lib/matplotlib/axes/_axes.py` line 5017

**Inconsistent comparison operators**:
- Line 5003 (C=None case): `accum[accum < mincnt] = np.nan` → keeps bins where count >= mincnt
- Line 5017 (C!=None case): `len(acc) > mincnt` → keeps bins where count > mincnt

**Evidence**:
```python
# Line 5002-5003 (C is None):
if mincnt is not None:
    accum[accum < mincnt] = np.nan  # Excludes count < mincnt, keeps count >= mincnt

# Line 5016-5017 (C is not None):
accum = np.array(
    [reduce_C_function(acc) if len(acc) > mincnt else np.nan  # Keeps count > mincnt only
     for Cs_at_i in [Cs_at_i1, Cs_at_i2]
     for acc in Cs_at_i[1:]],
    float)
```

**Verification**: Manual test confirms:
- Without C, mincnt=1: 3 hexbins shown (values: [2., 1., 1.])
- With C, mincnt=1: 1 hexbin shown (values: [2.])

**Fix**: Change line 5017 from `len(acc) > mincnt` to `len(acc) >= mincnt`

Confidence: **deduction - 99%** (directly traced through code logic and verified with test)

---

## Craft: Gate Loop

### Iteration 1 - Implementation

**Diagnosis Review:**
Root cause confirmed: inconsistent comparison operators between C=None and C!=None paths in hexbin method.
- C=None path: `accum[accum < mincnt]` keeps bins with count >= mincnt
- C!=None path: `len(acc) > mincnt` keeps bins with count > mincnt
- With mincnt=1: C=None shows 3 hexbins, C!=None shows 1 hexbin

**Codex Volley 1:**
Initial draft changed only comparison operator `>` to `>=` at line 5017.

Codex feedback: Incomplete fix breaks default behavior when mincnt=None.
- Current: `mincnt=None → 0`, then `len(acc) > 0` (filters empty bins)
- Proposed: `mincnt=None → 0`, then `len(acc) >= 0` (includes empty bins, can break reduce_C_function)
- Issue: Functions like np.amax, np.min raise ValueError on empty arrays

**Codex Volley 2:**
Revised to change both:
1. Line 5015: `mincnt = 0` → `mincnt = 1`
2. Line 5017: `len(acc) > mincnt` → `len(acc) >= mincnt`

This preserves default behavior (filter to bins with >= 1 point) while fixing the off-by-one error for explicit mincnt values. Codex confirmed this matches matplotlib documentation that states default should filter to "at least 1 point" to avoid reduction function errors.

**Applied Changes:**
```diff
--- a/lib/matplotlib/axes/_axes.py
+++ b/lib/matplotlib/axes/_axes.py
@@ -5013,8 +5013,8 @@ class Axes(_AxesBase):
                     Cs_at_i2[i2[i]].append(C[i])
             if mincnt is None:
-                mincnt = 0
+                mincnt = 1
             accum = np.array(
-                [reduce_C_function(acc) if len(acc) > mincnt else np.nan
+                [reduce_C_function(acc) if len(acc) >= mincnt else np.nan
                  for Cs_at_i in [Cs_at_i1, Cs_at_i2]
                  for acc in Cs_at_i[1:]],
                 float)
```

**Gate Result:**
```
lib/matplotlib/tests/test_axes.py::test_hexbin_mincnt_behavior_upon_C_parameter[png] PASSED
============================== 1 passed in 0.39s ===============================
```

All tests in test_axes.py passed: 813 passed, 66 skipped

**Trajectory:** Convergent-resolved ✓

**Resolution:** FAIL_TO_PASS test passes. Fix makes both code paths use consistent semantics for mincnt parameter.

---

## Audit: matplotlib__matplotlib-26113

### Phase 1: Patch confirmation
```
git diff --stat
 lib/matplotlib/axes/_axes.py | 4 ++--
 1 file changed, 2 insertions(+), 2 deletions(-)
```
Patch is live.

### Phase 2: Gate execution
Full gate run: 813 passed, 66 skipped in 45.97s

### Phase 3: Classification against baseline

#### FAIL_TO_PASS
- `lib/matplotlib/tests/test_axes.py::test_hexbin_mincnt_behavior_upon_C_parameter[png]`: **PASSED** ✓

#### PASS_TO_PASS regressions
**None.** All 813 tests passed, no failures detected.

#### Pre-existing failures
**None.** The 66 skipped tests are due to missing dependencies (Inkscape for SVG conversion), not failures. Baseline capture shows the same pattern.

### Phase 4: Verdict

**Condition met:** All FAIL_TO_PASS pass (1/1) AND zero PASS_TO_PASS regressions (0/813).

Contract fulfilled:
- Target test now passes: hexbin with C parameter and mincnt=1 shows 3 hexbins (matching C=None behavior)
- No regressions introduced: full test suite clean
- Fix is minimal and surgical: 2-line change aligning comparison operators

**VERDICT: RESOLVED**
**RE-ENTER: none**
