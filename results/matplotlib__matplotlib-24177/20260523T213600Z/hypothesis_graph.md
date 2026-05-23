# Hypothesis graph: matplotlib__matplotlib-24177

---
## Hypothesis Node: Initial Diagnosis (Recon Round 1)
**Type**: Abduction  
**Confidence**: 98% (deduction)  
**Status**: Proposed

### Observation
Test `test_small_autoscale` fails with assertion `assert 0.25 >= 0.33`. A PathPatch with 132 vertices (max y=0.33) is added and autoscaled, but ylim[1] only reaches 0.25.

### Root Cause
Path simplification discards vertices during data limit calculation. When `len(vertices) >= 128`, matplotlib sets `should_simplify=True`. The `_update_patch_limits` method calls `p.iter_bezier()` which applies this simplification, reducing 132 segments to 11 and losing vertices with y=0.33.

### Evidence
1. `lib/matplotlib/axes/_base.py:2435` — `for curve, code in p.iter_bezier():` (no simplify=False)
2. `lib/matplotlib/path.py:203-209` — Enables simplification when `len(self._vertices) >= 128`
3. Experiment: `iter_bezier(simplify=False)` processes all 132 segments, max y=0.33 ✓
4. Experiment: `iter_bezier()` (default) processes only 11 segments, max y=0.25 ✗

### Proposed Fix
`lib/matplotlib/axes/_base.py:2435` — Change `p.iter_bezier()` to `p.iter_bezier(simplify=False)`

### Killed Alternatives
- Bezier extrema calculation bug — No, works correctly without simplification
- Floating-point tolerance — No, raw data limits are 0.25 before margin expansion  
- Transform error — No, vertices have max y=0.25 before transformation

### Prediction
Adding `simplify=False` will cause `test_small_autoscale` to pass with ylim[1] >= 0.33.

## Gate Loop

### Iteration 1: Initial fix applied

**Change**: Added `simplify=False` to `iter_bezier()` call in `_update_patch_limits` at line 2437 of `lib/matplotlib/axes/_base.py`

**Codex review**: Approved. The change is conceptually correct - autoscale/data-limit calculation must not use path simplification. Performance impact is acceptable for correctness.

**Gate result**: ✅ **PASSED**
- FAIL_TO_PASS test `lib/matplotlib/tests/test_axes.py::test_small_autoscale` now passes
- All 769 tests passed, 64 skipped
- No regressions

**Trajectory**: Convergent-resolved (first iteration success)

**Resolution**: The one-line fix prevents path simplification from discarding vertices during axis limit calculation, ensuring autoscale correctly captures the full extent of paths with ≥128 vertices.

---
## Audit: matplotlib-24177

**Patch**: 
```diff
lib/matplotlib/axes/_base.py:2437
-        for curve, code in p.iter_bezier():
+        for curve, code in p.iter_bezier(simplify=False):
```

### FAIL_TO_PASS
- `lib/matplotlib/tests/test_axes.py::test_small_autoscale`: **PASSED** ✓

### PASS_TO_PASS regressions
None. All 769 tests passed, 64 skipped.

### Pre-existing failures (not counted)
None. Gate output matches fail-on-base baseline (769 passed, 64 skipped on both).

### Kill report
N/A — Fix is **RESOLVED**.

**VERDICT**: RESOLVED  
**RE-ENTER**: none

The single-line patch correctly prevents path simplification from discarding vertices during autoscale limit calculation. The FAIL_TO_PASS test now passes, and no PASS_TO_PASS tests regressed.
