# Hypothesis graph: matplotlib__matplotlib-20859

## H₀ (abduction)

**Claim**: The tests fail because `Legend.__init__` only accepts `Axes` or `Figure` parent types, but `SubFigure` is a sibling class of `Figure` (both inherit from `FigureBase`), so SubFigure instances are rejected.

**Evidence**:
- Error message: `TypeError: Legend needs either Axes or Figure as parent` at `lib/matplotlib/legend.py:441`
- `SubFigure` class inherits from `FigureBase` (`lib/matplotlib/figure.py:1924`)
- `Figure` class inherits from `FigureBase` (`lib/matplotlib/figure.py:2112`)  
- `Legend.__init__` checks `isinstance(parent, Figure)` (`lib/matplotlib/legend.py:437`), which returns False for SubFigure instances
- The `legend()` method is defined in `FigureBase` (line 941), so both Figure and SubFigure can call it
- When `SubFigure.legend()` is called, it passes `self` to `Legend(self, ...)` (line 1068), which triggers the type check

**Confidence**: Deduction — 98%

**Root cause**: Line 437 in `lib/matplotlib/legend.py` checks `isinstance(parent, Figure)` instead of `isinstance(parent, FigureBase)`, causing SubFigure instances to be rejected.

**Fix**: Change the type check from `Figure` to `FigureBase` and import `FigureBase` from `matplotlib.figure`.


## Craft gate loop

### Iteration 1: Initial fix

**Changes applied:**
- `lib/matplotlib/legend.py:363`: Changed `from matplotlib.figure import Figure` to `from matplotlib.figure import FigureBase`
- `lib/matplotlib/legend.py:437`: Changed `isinstance(parent, Figure)` to `isinstance(parent, FigureBase)`
- `lib/matplotlib/legend.py:441`: Updated error message from "Legend needs either Axes or Figure as parent" to "Legend needs either Axes or FigureBase as parent"

**Codex volley feedback:**
- Confirmed removing `Figure` from import since it's unused after the change
- Suggested updating error message to mention FigureBase
- Noted low breakage risk since FigureBase is the shared base for Figure and SubFigure

**Gate result:** ✓ PASS
- test_subfigure_legend: PASSED
- All 89 tests passed, 10 skipped, 0 failures

**Resolution:** The fix correctly enables `SubFigure.legend()` by accepting all `FigureBase` subclasses (Figure and SubFigure) as valid legend parents.


## Audit: matplotlib__matplotlib-20859

**Patch confirmed live:** 1 file changed, 3 insertions(+), 3 deletions(-)

### FAIL_TO_PASS
- `lib/matplotlib/tests/test_legend.py::test_subfigure_legend`: **PASS** ✓

### PASS_TO_PASS regressions
None — all 89 tests passed.

### Pre-existing failures (not counted, confirmed against base capture)
None — the only pre-existing failure was `test_subfigure_legend`, which is now resolved.

### Summary
The patch successfully resolves the issue. The `test_subfigure_legend` test that was failing on base with `TypeError: Legend needs either Axes or Figure as parent` now passes. No regressions were introduced — all PASS_TO_PASS tests remain passing.

**Final gate result:** 89 passed, 10 skipped, 0 failures
