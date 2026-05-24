# Hypothesis graph: matplotlib__matplotlib-20676

## Hypothesis H1 (Abduction → Deduction)
**Timestamp**: Initial diagnosis  
**Claim**: SpanSelector with `interactive=True` incorrectly expands axes limits to include 0 because `_setup_edge_handle` creates axvline/axhline at position (0, 0) during initialization.

**Evidence**:
1. Test failure shows axes bounds change from (10.0, 20.0) to (0.0, 20.0) after creating SpanSelector
2. Code trace:
   - `SpanSelector.__init__` calls `new_axes(ax)` which creates `_rect` at position (0, 0)
   - Then if `interactive=True`, calls `_setup_edge_handle(props)`
   - `_setup_edge_handle` at line 2159 passes `self.extents` to `ToolLineHandles`
   - `self.extents` property reads from `_rect` which is at (0, 0), returning (0, 0)
   - `ToolLineHandles.__init__` creates `axvline(0)` or `axhline(0)` for each position
   - Even with `visible=False`, axvline/axhline expand axes to include their position

3. Experimental confirmation:
```
Before SpanSelector: x_bound: (9.5, 20.5)
After SpanSelector:  x_bound: (-1.0, 21.0)  # expanded to include 0
edge_handles.positions: [0, 0]  # initialized at wrong position
```

4. Test expectation confirms fix:
```python
bound = x_bound if direction == 'horizontal' else y_bound
assert tool._edge_handles.positions == list(bound)
```
Test expects edge handles at current axes bounds, not at (0, 0).

**Root cause**: Line 2159 in `_setup_edge_handle` passes `self.extents` which returns (0, 0) from the just-initialized rectangle, instead of passing the current axes bounds.

**Confidence**: Deduction, 99% — traced code path, reproduced bug, verified axvline behavior.

**Edit site**:
- `lib/matplotlib/widgets.py` lines 2158-2163 (`_setup_edge_handle` method)
  - Replace `self.extents` with axes bounds: `self.ax.get_xbound()` for horizontal, `self.ax.get_ybound()` for vertical


## Craft: Gate Loop

### Iteration 1: Initial fix

**Hypothesis**: The edge handles are initialized at (0, 0) because `_setup_edge_handle` passes `self.extents`, which reads from the rectangle that's positioned at (0, 0). Passing `ax.get_xbound()`/`ax.get_ybound()` instead will initialize handles at current axes bounds.

**Implementation**:
```python
def _setup_edge_handle(self, props):
    if self.direction == 'horizontal':
        positions = self.ax.get_xbound()
    else:
        positions = self.ax.get_ybound()
    self._edge_handles = ToolLineHandles(self.ax, positions,
                                         direction=self.direction,
                                         line_props=props,
                                         useblit=self.useblit)
```

**codex review**: Approved. "Patch is fine" — correctly initializes handles at current data bounds to prevent autoscaling to include 0.

**Gate result**: ✅ **CONVERGENT-RESOLVED**
- `test_span_selector_bound[horizontal]` — PASSED
- `test_span_selector_bound[vertical]` — PASSED

Both FAIL_TO_PASS tests now pass. 

**Note**: `test_rectangle_selector` shows 1 failure, but this is a pre-existing issue (verified by stashing changes and re-running — it fails on unmodified code). The failure is about deprecation warnings in RectangleSelector, completely unrelated to the SpanSelector fix.

**E-value**: Convergent-resolved (FAIL_TO_PASS tests pass on first attempt)


## Audit: matplotlib__matplotlib-20676

**Full gate run**: 36 tests collected, 34 passed, 1 failed, 1 skipped

### FAIL_TO_PASS
- `test_span_selector_bound[horizontal]`: **PASSED** ✓
- `test_span_selector_bound[vertical]`: **PASSED** ✓

### PASS_TO_PASS regressions
**None** — all PASS_TO_PASS tests remain passing.

### Pre-existing failures (not counted, confirmed against base capture)
- `test_rectangle_selector`: Failed on base with MatplotlibDeprecationWarning, still fails (unrelated to SpanSelector fix)

### Patch summary
```diff
lib/matplotlib/widgets.py | 6 +++++-
1 file changed, 5 insertions(+), 1 deletion(-)
```

The fix correctly initializes edge handles with `ax.get_xbound()`/`ax.get_ybound()` instead of `self.extents`, preventing axes limit expansion to include (0, 0).

**Contract satisfied**:
- All FAIL_TO_PASS tests now pass: ✓
- Zero PASS_TO_PASS regressions: ✓
