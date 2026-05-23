# Hypothesis graph: matplotlib__matplotlib-26208

## H₀ (Baseline - Abduction)
**Timestamp:** 2026-05-23
**Status:** Active
**Type:** Abduction
**Confidence:** 85%

The tests fail because when creating twin axes via `twinx()` or `twiny()`, the `units` attribute of the shared axis is not copied from the original axis to the twin axis.

**Evidence:**
- Test `test_twin_units[x]` fails at assertion: `assert getattr(ax2, axis_name).units is not None`
- After `ax1.plot(a, b)` with string arrays, `ax1.xaxis.units` is a `UnitData` object
- After `ax2 = ax1.twinx()`, `ax2.xaxis.units` is `None` (should be the same object as `ax1.xaxis.units`)
- Similarly for `twiny()`, `ax2.yaxis.units` is `None` when it should be shared

**Root Cause:**
In `lib/matplotlib/axes/_base.py`, the `sharex()` and `sharey()` methods (lines 1221-1257) copy several attributes from the shared axis:
- `major` and `minor` (ticker instances)
- limits via `set_xlim()`/`set_ylim()`
- `_scale`

But they do NOT copy the `units` attribute, which is needed for converting non-numeric data (like strings) to plot coordinates.

**Historical Context:**
The `sharex()` and `sharey()` methods were introduced in commit 83c2d7b6b5 (Sept 2019) and never included units copying. This has been a latent bug since then.

**Edit Sites:**
- `lib/matplotlib/axes/_base.py` line ~1237 (in `sharex()` method): Add `self.xaxis.units = other.xaxis.units`
- `lib/matplotlib/axes/_base.py` line ~1255 (in `sharey()` method): Add `self.yaxis.units = other.yaxis.units`

**Next Steps:**
Add unit sharing to both `sharex()` and `sharey()` methods, immediately after copying the major/minor tickers and before setting limits.

## Implementation (Craft)
**Timestamp:** 2026-05-23
**Status:** Resolved
**Gate Iteration:** 1/8

### Codex Pre-Gate Review
Drafted initial fix adding two lines to each method:
- `sharex()`: `self.xaxis.units = other.xaxis.units` and `self.xaxis.converter = other.xaxis.converter`
- `sharey()`: `self.yaxis.units = other.yaxis.units` and `self.yaxis.converter = other.yaxis.converter`

Codex feedback highlighted that the fix should also copy `converter` (not just `units`), which is needed to convert non-numeric data. Codex suggested using proper API methods (`set_units()`, `get_units()`) instead of direct assignment, but after reviewing the codebase:
- No setter exists for `converter` (always set directly in `update_units()`)
- `sharex()`/`sharey()` already use direct assignment for `major`, `minor`, `_scale`
- Using direct assignment maintains consistency with existing code patterns

Recon handoff mentioned copying `units` and `converter`, so added both.

### Gate Iteration 1: PASSED
Applied fix at lines 1237-1238 (sharex) and 1257-1258 (sharey):
```python
self.xaxis.units = other.xaxis.units
self.xaxis.converter = other.xaxis.converter
```

**Result:** All tests passed (815 passed, 66 skipped)
- `test_twin_units[x]`: PASSED
- `test_twin_units[y]`: PASSED

**Trajectory:** Convergent success - FAIL_TO_PASS tests now pass on first gate run.

### Resolution
The fix successfully copies both `units` and `converter` attributes when axes are shared, ensuring that twin axes inherit the unit conversion capability from their parent axes. This allows non-numeric data (like strings) to be properly handled on twinned axes.

## Audit: matplotlib__matplotlib-26208
**Timestamp:** 2026-05-23
**Status:** RESOLVED

### Phase 1: Patch Confirmation
```
lib/matplotlib/axes/_base.py | 4 ++++
1 file changed, 4 insertions(+)
```
Patch is live: craft added 4 lines copying `units` and `converter` attributes in `sharex()` and `sharey()` methods.

### Phase 2: Gate Execution
Full test suite run completed: **815 passed, 66 skipped** in 45.54s

### Phase 3: Classification

#### FAIL_TO_PASS (both now PASS ✓)
- `lib/matplotlib/tests/test_axes.py::test_twin_units[x]`: **PASSED**
- `lib/matplotlib/tests/test_axes.py::test_twin_units[y]`: **PASSED**

#### PASS_TO_PASS Regressions
**None.** All 815 tests in the suite passed, consistent with baseline.

#### Pre-existing Failures (not counted)
**None.** Baseline showed all tests passing; current run matches baseline.

### Phase 4: Verdict

**Contract fulfilled:**
- ✓ All FAIL_TO_PASS tests now pass (2/2)
- ✓ Zero PASS_TO_PASS regressions (0 regressions)
- ✓ No new test failures introduced

The fix successfully copies `units` and `converter` attributes when axes are shared via `sharex()`/`sharey()`, enabling twin axes to properly handle non-numeric (e.g., string) data. The patch is minimal (4 lines), follows existing code patterns (direct attribute assignment matching `major`/`minor`/`_scale`), and introduces no regressions.

VERDICT: RESOLVED
RE-ENTER: none
