# Hypothesis graph: matplotlib__matplotlib-23314

## H₀: Missing visibility check in Axes3D.draw()

**Type**: Abduction  
**Status**: Active  
**Timestamp**: 2026-05-23

### Failure mode
The test `test_invisible_axes[png]` fails with image comparison error (RMS 17.513). The test creates a 3D axes, calls `set_visible(False)`, but the axes remains visible in the output image.

### Root cause
The `Axes3D.draw()` method in `lib/mpl_toolkits/mplot3d/axes3d.py` (line 389) does NOT check visibility before drawing 3D-specific elements. 

The parent `Axes.draw()` method in `lib/matplotlib/axes/_base.py` (lines 3021-3022) checks visibility:
```python
if not self.get_visible():
    return
```

However, `Axes3D.draw()` performs 3D-specific drawing BEFORE calling `super().draw()`:
- Line 393: draws the background patch
- Lines 435-441: draws 3D axis panes and axes (if `_axis3don` is True)
- Line 443: calls `super().draw(renderer)` which DOES check visibility

By the time `super().draw()` returns early due to the visibility check, all the 3D-specific elements have already been rendered.

### Evidence
- `lib/mpl_toolkits/mplot3d/axes3d.py:389-443` - Axes3D.draw() method lacks visibility check
- `lib/matplotlib/axes/_base.py:3021-3022` - Parent Axes.draw() has visibility check
- `lib/matplotlib/tests/test_axes.py:test_invisible_axes` - 2D version works correctly
- `git blame` shows the draw method is from 2009, predating robust visibility handling

### Confidence
**Deduction** — 95%

The code path is clear: Axes3D.draw() draws elements before checking visibility via super().draw(). The 2D version works because the check happens at the start of Axes.draw().

### Edit site
- `lib/mpl_toolkits/mplot3d/axes3d.py` lines 389-391: Add visibility check at the start of `draw()` method, before any drawing operations.


## Gate Loop 1 (craft)

**Hypothesis**: Adding visibility check at the start of `Axes3D.draw()` (before any rendering) will prevent 3D elements from being drawn when axes is invisible.

**Diff applied**:
```diff
--- a/lib/mpl_toolkits/mplot3d/axes3d.py
+++ b/lib/mpl_toolkits/mplot3d/axes3d.py
@@ -389,6 +389,8 @@
     @martist.allow_rasterization
     def draw(self, renderer):
+        if not self.get_visible():
+            return
         self._unstale_viewLim()
```

**codex pre-gate review**: No functional issue. The early visibility guard matches `Axes.draw()` semantics. Skipping `_unstale_viewLim()`, patch.draw, pane drawing, and projection computation when invisible is correct. No obvious breaks.

**Gate result**: ✓ PASSED (864 passed, 63 skipped)
- `test_invisible_axes[png]` PASSED
- All other tests PASSED

**Trajectory**: Convergent (green) — fix correctly addresses root cause on first attempt.

**Resolution**: RESOLVED — FAIL_TO_PASS test passes, no regressions.


## Audit: matplotlib-23314

### Phase 1: Patch verification
```
lib/mpl_toolkits/mplot3d/axes3d.py | 2 ++
1 file changed, 2 insertions(+)
```
Patch is live: 2-line addition to Axes3D.draw() method.

### Phase 2: Gate execution
Full gate run completed: 864 passed, 63 skipped in 66.62s

### Phase 3: Classification

**FAIL_TO_PASS**
- `lib/mpl_toolkits/tests/test_mplot3d.py::test_invisible_axes[png]`: **PASS** ✓

**PASS_TO_PASS regressions**
None — all 864 tests passed.

**Pre-existing failures**
None — no failures observed in gate output.

### Phase 4: Verdict
All FAIL_TO_PASS tests pass (1/1). Zero regressions. Clean pass.

**VERDICT**: RESOLVED  
**RE-ENTER**: none
