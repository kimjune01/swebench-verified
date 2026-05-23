# Hypothesis graph: matplotlib__matplotlib-24627

## H₀: Initial observation (abduction)
The test `test_cla_clears_children_axes_and_fig` fails because after calling `ax.clear()`, the `.axes` and `.figure` attributes of deparented artists remain set to the Axes and Figure objects instead of being set to `None`.

**Evidence:**
- Test assertion failure: `assert art.axes is None` fails with `assert <Axes: > is None`
- Location: lib/matplotlib/tests/test_axes.py:8382

## H₁: Root cause - __clear() doesn't unset artist attributes (deduction - 95%)

`Axes.__clear()` clears the children list by setting `self._children = []` without first unsetting the `.axes` and `.figure` attributes of the deparented artists.

**Evidence:**
- lib/matplotlib/axes/_base.py:1310: `self._children = []` — clears children without unsetting their attributes
- lib/matplotlib/artist.py:220: `self.axes = None` — the `remove()` method correctly unsets axes
- lib/matplotlib/artist.py:223: `self.figure = None` — the `remove()` method correctly unsets figure
- Problem statement confirms: `l.remove()` sets axes to None, but `a.cla()` doesn't

**Call path:**
1. Test calls `ax.clear()` (line 8381 in test_axes.py)
2. `clear()` delegates to `__clear()` via `cla()` (lines 1395-1414 in _base.py)
3. `__clear()` sets `self._children = []` (line 1310 in _base.py) without iterating through children first
4. Artists remain with stale `.axes` and `.figure` references

**Supporting pattern:**
The `Artist.remove()` method demonstrates the correct behavior:
- Lines 211-220: When removing an artist, it explicitly sets `self.axes = None`
- Lines 223-226: It also sets `self.figure = None`
- This pattern should be replicated in `__clear()` before clearing `self._children`

## Rejected hypotheses
None yet (first iteration).

## Open questions
None.

## craft iteration 1

**Hypothesis**: Recon diagnosis correct - `__clear()` clears `self._children = []` without unsetting `.axes` and `.figure` attributes on deparented children.

**Edit**: `lib/matplotlib/axes/_base.py` lines 1307-1318
- Swap `self._children` to `old_children` before clearing
- Iterate through `old_children` and set:
  - `child._remove_method = None`
  - `child.stale_callback = None`
  - `child.axes = None`
  - `child.figure = None`
- Pattern mirrors `Artist.remove()` cleanup semantics

**codex volley**:
- Round 1: Suggested handling `_remove_method`, `stale_callback`, and swap pattern
- Round 2: Confirmed to leave `child_axes` alone (test doesn't cover it, figure bookkeeping risk)
- Approved final minimal fix

**Gate result**: ✅ PASS
- `test_cla_clears_children_axes_and_fig` passes
- All 777 tests passed, 64 skipped
- No regressions

**Trajectory**: Convergent (resolved in 1 iteration)

## Audit: matplotlib__matplotlib-24627

### FAIL_TO_PASS
- `test_cla_clears_children_axes_and_fig`: **PASSED** ✓

### PASS_TO_PASS regressions
None. All 777 tests passed.

### Pre-existing failures (not counted)
None. Gate output: 777 passed, 64 skipped, 0 failed.

### Kill report
Not applicable — fix is RESOLVED.

**VERDICT**: RESOLVED
**RE-ENTER**: none

