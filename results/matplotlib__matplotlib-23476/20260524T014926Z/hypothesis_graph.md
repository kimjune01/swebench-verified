# Hypothesis graph: matplotlib__matplotlib-23476

---

## Hypothesis H0 [ACTIVE]
**Mode:** deduction  
**Confidence:** 99%  
**Timestamp:** 2026-05-23

### Symptom
Test `test_unpickle_with_device_pixel_ratio` fails: after pickling a figure with dpi=42 and device_pixel_ratio=7, unpickling returns a figure with dpi=294 instead of the expected dpi=42.

### Root Cause
`FigureCanvasBase.__init__` (backend_bases.py:1656) unconditionally sets `figure._original_dpi = figure.dpi`, which overwrites the pickled `_original_dpi` value during unpickling.

When unpickling:
1. `Figure.__setstate__` restores `_dpi=294` and `_original_dpi=42` from pickle
2. Creates new canvas with `FigureCanvasBase(self)`
3. Canvas init overwrites: `_original_dpi = figure.dpi` → `_original_dpi = 294`
4. Result: both `_dpi` and `_original_dpi` are 294 (should be 294 and 42)

### Evidence
- backend_bases.py:1656: unconditional assignment `figure._original_dpi = figure.dpi`
- backend_bases.py:2104: uses `_original_dpi` to scale by device_pixel_ratio
- figure.py:3047: creates canvas after restoring pickle state
- Test script confirms `_original_dpi` is 294 after unpickle (should be 42)

### Edit Site
`lib/matplotlib/backend_bases.py` line 1656: Change from unconditional assignment to conditional:
```python
# Before:
figure._original_dpi = figure.dpi

# After (option 1):
if not hasattr(figure, '_original_dpi'):
    figure._original_dpi = figure.dpi

# After (option 2):
figure._original_dpi = getattr(figure, '_original_dpi', figure.dpi)
```

### Expected Fix
Preserves pickled `_original_dpi` during unpickling while still initializing it during normal figure creation.

## craft iteration 1: fix applied

**Hypothesis**: Figure.__getstate__ needs to serialize logical DPI instead of effective DPI.

**Evidence**: codex review identified that the original recon diagnosis was incomplete — the backend fix alone would preserve `_original_dpi` but still pickle the effective DPI, leaving `fig2.dpi == 294` after unpickling.

**Change**: Added `state["_dpi"] = state.get("_original_dpi", state["_dpi"])` to `Figure.__getstate__` after popping canvas (lib/matplotlib/figure.py:3023-3025).

**Gate result**: ✅ PASS
- test_unpickle_with_device_pixel_ratio: PASSED
- All 105 tests passed, 7 skipped
- Elapsed: 9.18s

**Trajectory**: Convergent (resolved on first iteration)

---

## Audit: matplotlib__matplotlib-23476

### Patch Verification
- Patch is live: `lib/matplotlib/figure.py | 3 insertions(+)`
- Change: Added DPI normalization in `Figure.__getstate__` to serialize logical DPI instead of effective DPI

### FAIL_TO_PASS Results
- `lib/matplotlib/tests/test_figure.py::test_unpickle_with_device_pixel_ratio`: **PASSED** ✅

### PASS_TO_PASS Regressions
None

### Pre-existing Failures
None (all skipped tests were already skipped on base)

### Test Suite Summary
- 105 passed, 7 skipped
- Gate execution time: 9.08s
- All FAIL_TO_PASS tests now pass
- Zero regressions introduced

### Patch Details
```diff
diff --git a/lib/matplotlib/figure.py b/lib/matplotlib/figure.py
index c55864243a..2bc30752db 100644
--- a/lib/matplotlib/figure.py
+++ b/lib/matplotlib/figure.py
@@ -3020,6 +3020,9 @@ class Figure(FigureBase):
         # re-attached to another.
         state.pop("canvas")
 
+
+        # discard any changes to the dpi due to pixel ratio changes
+        state["_dpi"] = state.get("_original_dpi", state["_dpi"])
         # Set cached renderer to None -- it can't be pickled.
         state["_cachedRenderer"] = None
```

**Fix Mechanism**: During pickle serialization, replace the effective DPI (which may have been scaled by device pixel ratio) with the original logical DPI. This ensures unpickled figures restore their pre-scaling DPI value.

