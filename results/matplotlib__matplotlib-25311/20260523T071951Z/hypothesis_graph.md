# Hypothesis graph: matplotlib__matplotlib-25311

## Hypothesis Node: DraggableBase stores unpicklable canvas reference

**Type**: Root cause identified (deduction)

**Evidence**:
1. Test `test_complete[png]` creates a legend with `draggable=True` (line 93 of test_pickle.py)
2. Test asserts "FigureCanvasAgg" not in pickle stream (line 99 of test_pickle.py)
3. When `legend.set_draggable(True)` is called, it creates a `DraggableLegend` object stored in `legend._draggable` (legend.py:1196-1198)
4. `DraggableLegend` inherits from `DraggableOffsetBox`, which inherits from `DraggableBase`
5. `DraggableBase.__init__` stores `self.canvas = self.ref_artist.figure.canvas` (offsetbox.py:1509)
6. When the figure is pickled, the legend is pickled, which pickles `_draggable`, which pickles the `canvas` reference

**Root cause**: `DraggableBase` stores a direct reference to the canvas (`self.canvas`) which is not picklable. Unlike `Figure` which has `__getstate__`/`__setstate__` methods to exclude the canvas, `DraggableBase` lacks these methods.

**Code path**:
- Legend.set_draggable(True) → DraggableLegend.__init__() → DraggableBase.__init__()
- DraggableBase.__init__ sets self.canvas (offsetbox.py:1509)
- Figure pickle → Legend pickle → DraggableLegend pickle → canvas reference pickled

**Confidence**: Deduction — 99% (traced code path, verified with existing Figure.__getstate__ pattern)

**Fix approach**: Add `__getstate__` and `__setstate__` methods to `DraggableBase` class to:
1. Exclude canvas and callback state (cids, _c1, background) during pickling
2. Restore canvas from `self.ref_artist.figure.canvas` and reconnect callbacks during unpickling

**Edit site**: lib/matplotlib/offsetbox.py, DraggableBase class (around line 1580, after finalize_offset method)

## Craft Gate Loop

### Iteration 1: Initial fix
- **Action**: Added `__getstate__` and `__setstate__` to `DraggableBase` class
- **Fix**: Exclude canvas-related attrs (`canvas`, `cids`, `_c1`, `background`) from pickle, reconnect on restore
- **Gate result**: FAILED - `AttributeError: 'Legend' object has no attribute 'figure'`
- **Evidence**: Unpickle ordering issue - `ref_artist.figure` not available when `__setstate__` runs
- **Trajectory**: Divergent - new error, reveals unpickle dependency

### Iteration 2: Handle unpickle ordering
- **Action**: Made canvas reconnection conditional on `ref_artist.figure` availability
- **Fix**: Added check `if hasattr(self.ref_artist, 'figure') and self.ref_artist.figure is not None`
- **Gate result**: test_complete[png] PASSED, test_pickle_load_from_subprocess[png] FAILED (version warning)
- **Evidence**: FAIL_TO_PASS test passes; remaining failure is UserWarning about version mismatch, unrelated to DraggableBase
- **Trajectory**: Convergent (success) - FAIL_TO_PASS test passes, other failure is test infrastructure issue

### Resolution
- **Status**: RESOLVED
- **Final fix**: `DraggableBase.__getstate__` excludes canvas refs; `__setstate__` conditionally reconnects
- **FAIL_TO_PASS**: test_complete[png] PASSES
- **Note**: test_pickle_load_from_subprocess failure is unrelated version warning (passes with `-W ignore`)
