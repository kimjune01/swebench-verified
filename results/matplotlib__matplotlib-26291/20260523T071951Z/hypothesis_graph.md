# Hypothesis Graph: matplotlib__matplotlib-26291

## H₀ (Initial Observation - Abduction)
**Status**: Confirmed  
**Confidence**: 99% (Deduction)  
**Timestamp**: 2026-05-22

The test `test_inset_axes_tight` fails because when `fig.savefig(f, bbox_inches="tight")` is called after creating inset axes, it raises:
```
AttributeError: 'NoneType' object has no attribute '_get_renderer'
```

**Stack trace**:
- `_tight_bbox.adjust_bbox` (line 28) calls `locator(ax, None)` with renderer=None
- `AnchoredLocatorBase.__call__` (line 73) calls `self.get_window_extent(renderer)`
- `OffsetBox.get_window_extent` (line 398) tries `self.figure._get_renderer()` when renderer is None
- But `self.figure` is None, causing AttributeError

## H₁ (Root Cause - Deduction)
**Status**: Active  
**Confidence**: 95% (Deduction)  
**Timestamp**: 2026-05-22

**Root cause**: `AnchoredLocatorBase.__call__` sets `self.axes = ax` but does not set `self.figure`, leaving it as None.

**Evidence**:
1. `lib/mpl_toolkits/axes_grid1/inset_locator.py:72` - `AnchoredLocatorBase.__call__` sets only `self.axes = ax`
2. `lib/matplotlib/offsetbox.py:398` - `get_window_extent` requires `self.figure` to be set when renderer is None
3. `AnchoredSizeLocator` (and `AnchoredZoomLocator`) inherit from `AnchoredLocatorBase` which inherits from `AnchoredOffsetbox` which inherits from `OffsetBox` which inherits from `Artist`
4. Artists normally get their `figure` attribute set when added to a figure, but locator objects are never added to the figure - they're just used as callbacks
5. When `_tight_bbox.adjust_bbox` is called during `savefig` with `bbox_inches="tight"`, it calls the locator with `renderer=None` to compute positions before the actual rendering

**Why this manifests now**:
- Normal rendering passes a valid renderer to the locator
- Only `bbox_inches="tight"` triggers the `_tight_bbox.adjust_bbox` code path that calls the locator with `renderer=None`
- When renderer is None, `get_window_extent` falls back to getting a renderer from `self.figure`

**Fix specification**:
In `AnchoredLocatorBase.__call__`, after setting `self.axes = ax`, also set `self.figure = ax.figure` (or call `self.set_figure(ax.figure)`).

---

## Craft gate-loop (matplotlib__matplotlib-26291)

### Iteration 1
**Hypothesis**: Setting `self.figure = ax.figure` after `self.axes = ax` will fix the AttributeError in `get_window_extent`.

**Edit**: Added `self.figure = ax.figure` at line 73 in `lib/mpl_toolkits/axes_grid1/inset_locator.py:__call__`

**Gate result**: FAIL (divergent/progress)
- Error moved from `get_window_extent` → `get_offset`
- New error: `AttributeError: 'NoneType' object has no attribute 'points_to_pixels'` in `offsetbox.py:1057`
- Progress: The first issue was fixed, but revealed a second issue where `renderer=None` is still passed to `get_offset`

**codex feedback**: The fix only handles `renderer=None` inside `get_window_extent` internally; it doesn't update the `renderer` variable in `__call__`. Need to normalize renderer once at the top so all downstream calls get a valid renderer.

### Iteration 2
**Hypothesis**: Normalize the renderer once at the start of `__call__` so both `get_window_extent` and `get_offset` receive a valid renderer.

**Edit**: Added renderer normalization after setting `self.figure`:
```python
if renderer is None:
    renderer = ax.figure._get_renderer()
```

**Gate result**: PASS ✓
- All 50 tests passed including `test_inset_axes_tight`
- Fix is complete and minimal

**Final diff**:
```diff
--- a/lib/mpl_toolkits/axes_grid1/inset_locator.py
+++ b/lib/mpl_toolkits/axes_grid1/inset_locator.py
@@ -70,6 +70,9 @@ class AnchoredLocatorBase(AnchoredOffsetbox):
 
     def __call__(self, ax, renderer):
         self.axes = ax
+        self.figure = ax.figure
+        if renderer is None:
+            renderer = ax.figure._get_renderer()
         bbox = self.get_window_extent(renderer)
         px, py = self.get_offset(bbox.width, bbox.height, 0, 0, renderer)
         bbox_canvas = Bbox.from_bounds(px, py, bbox.width, bbox.height)
```

**Resolution**: RESOLVED - The fix addresses the root cause identified by recon. When `savefig` calls the locator with `renderer=None`, we now set `self.figure` and normalize the renderer before using it, preventing AttributeErrors in both `get_window_extent` and `get_offset`.

---

# Audit: matplotlib__matplotlib-26291

## FAIL_TO_PASS
- `lib/mpl_toolkits/axes_grid1/tests/test_axes_grid1.py::test_inset_axes_tight` — **PASSED** ✓

## PASS_TO_PASS regressions
None. All 49 PASS_TO_PASS tests remain passing.

## Pre-existing failures (not counted)
None.

## Summary
The craft patch successfully resolves the issue. The fix adds:
1. `self.figure = ax.figure` to populate the figure attribute
2. Renderer normalization when `renderer is None` to get a valid renderer from `ax.figure._get_renderer()`

This prevents the AttributeError when `savefig(bbox_inches="tight")` calls the locator with `renderer=None`. All 50 tests pass with zero regressions.

VERDICT: RESOLVED
RE-ENTER: none
