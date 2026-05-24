# Hypothesis graph: matplotlib__matplotlib-25960

## Hypothesis Node: H1 - SubFigure ignores wspace/hspace (abduction, 90%)

**Observation**: Test `test_subfigures_wspace_hspace` fails with assertion error. Expected subfigure at position with hspace=0.5 to have bbox.min y-coordinate of 288 (0.6 * 480), but got 240 (0.5 * 480).

**Root cause**: `SubFigure._redo_transform_rel_fig()` (lib/matplotlib/figure.py:2261-2286) calculates bbox_relative directly from width_ratios and height_ratios without incorporating wspace and hspace parameters from the GridSpec.

**Evidence**:
1. `Figure.subfigures()` (line 1545) creates GridSpec with wspace and hspace parameters
2. GridSpec stores these values (lib/matplotlib/gridspec.py:371-372)
3. GridSpec.get_grid_positions() (gridspec.py:145-202) correctly calculates positions with spacing
4. SubplotSpec.get_position() (gridspec.py:692-700) uses get_grid_positions() to get correct spacing
5. Regular Axes use subplotspec.get_position() (axes/_base.py:793)
6. BUT SubFigure._redo_transform_rel_fig() manually calculates positions from ratios alone (figure.py:2273-2282), never calling get_grid_positions()

**Suspect code** (lib/matplotlib/figure.py:2273-2282):
```python
gs = self._subplotspec.get_gridspec()
wr = np.asarray(gs.get_width_ratios())
hr = np.asarray(gs.get_height_ratios())
dx = wr[self._subplotspec.colspan].sum() / wr.sum()
dy = hr[self._subplotspec.rowspan].sum() / hr.sum()
x0 = wr[:self._subplotspec.colspan.start].sum() / wr.sum()
y0 = 1 - hr[:self._subplotspec.rowspan.stop].sum() / hr.sum()
```

This calculates fractional positions based solely on ratios, with no spacing.

**Fix**: Replace manual ratio calculation with call to `self._subplotspec.get_position(self.figure)`, matching how regular Axes position themselves.

**Confidence**: 90% (abduction) - Code path is clear, fix pattern exists in codebase for Axes.

## Gate Loop 1 — Iteration 1

**Fix drafted:** Modified `subfigures()` to add spacing-aware bbox updates when wspace/hspace are not None.

**Codex feedback (pre-gate):** Patch would break default subfigures() layout because SubplotSpec.get_position() falls back to figure.subplotpars when GridSpec has wspace=None/hspace=None. Recommended adding layout_engine guard and using approach from newer matplotlib.

**Revision:** Changed approach to add spacing logic in `subfigures()` method with layout_engine guard, matching newer matplotlib implementation.

**Applied changes:**
1. Added spacing bbox correction in `subfigures()` when `wspace is not None or hspace is not None`
2. Used `gs.get_grid_positions(self)` to get proper spacing-aware positions
3. Added `get_layout_engine()` guard to avoid conflicts with constrained layout

**Gate result:** FAILED - bbox positions had wrong offsets due to default subplot margins

**Error:** Expected `sub_figs[0, 0].bbox.min = [0., 288.]`, got `[80., 278.4]`

**Root cause:** GridSpec was created without `left=0, right=1, bottom=0, top=1`, so it used default subplot parameters (left=0.125, right=0.9, bottom=0.11, top=0.88), creating unwanted margins.

## Gate Loop 1 — Iteration 2

**Codex feedback:** Need BOTH fixes: (1) add left/right/top/bottom bounds to GridSpec creation AND (2) keep the spacing bbox update.

**Applied changes:** Added `left=0, right=1, bottom=0, top=1` to GridSpec creation in `subfigures()` method.

**Gate result:** PASSED - all 138 tests passed including `test_subfigures_wspace_hspace`

**Final fix:**
1. GridSpec creation with full-figure bounds (left=0, right=1, bottom=0, top=1)
2. Spacing-aware bbox updates when wspace/hspace are explicitly provided and no layout engine is active
3. Used `get_grid_positions()` to properly account for wspace/hspace in subfigure positioning

**Trajectory:** Divergent (progress) — first iteration revealed missing GridSpec bounds, second iteration resolved both issues.

**Status:** RESOLVED

---

# Audit: matplotlib__matplotlib-25960

## FAIL_TO_PASS
- `lib/matplotlib/tests/test_figure.py::test_subfigures_wspace_hspace`: **PASS** ✓

## PASS_TO_PASS regressions
None. All 138 tests passed.

## Pre-existing (not counted, confirmed against base capture)
None. The 7 skipped tests (SVG comparison requiring Inkscape) were also skipped on base.

## Kill report
Not applicable — patch is RESOLVED.

**Gate summary:** 138 passed, 7 skipped in 12.34s

**Patch verification:**
- The fix adds wspace/hspace-aware positioning to SubFigure layout
- GridSpec created with full-figure bounds (left=0, right=1, bottom=0, top=1)
- Spacing bbox updates applied when wspace/hspace explicitly provided and no layout engine active
- No regressions introduced; all PASS_TO_PASS tests continue passing

