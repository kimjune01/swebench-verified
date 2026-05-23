# Hypothesis graph: matplotlib__matplotlib-24026

## H₀ (abduction): stackplot fails with CN color references

**Observation:** Test fails with `ValueError: Cannot put cycle reference ('C0') in prop_cycler` when calling `ax.stackplot(..., colors=["C0", "C1", "C2"])`

**Evidence:**
- Error originates at `lib/matplotlib/rcsetup.py:285` in `validate_color_for_prop_cycle`
- Stack trace shows call path: `test_stackplot` → `stackplot` (line 73) → `set_prop_cycle` → `cycler` → `validate_color_for_prop_cycle`
- The validator explicitly rejects CN references: `if isinstance(s, str) and re.match("^C[0-9]$", s): raise ValueError`

**Root cause:** stackplot.py:73 calls `axes.set_prop_cycle(color=colors)` with user-provided colors that may include CN references. The validation logic forbids CN references in property cycles because they're meant to be resolved *from* the cycle, not put *into* it (circular dependency).

**Confidence:** deduction (95%) - traced code path, read validation logic, reproduced error

## Fix strategy (deduction)

**Solution:** Instead of modifying the axes property cycle:
1. Resolve CN color references to actual RGBA colors using `matplotlib.colors.to_rgba()`
2. Create a local color iterator using `itertools.cycle`
3. Get colors from the local iterator instead of `axes._get_lines.get_next_color()`

**Benefits:**
- Accepts CN color references (fixes the bug)
- Doesn't modify axes cycler (fixes the issue title requirement: "stackplot should not change Axes cycler")

**Supporting code:**
- `lib/matplotlib/colors.py:290` - `to_rgba()` resolves CN references via `_is_nth_color()` check
- `lib/matplotlib/colors.py:213` - `_is_nth_color()` detects CN patterns: `re.match(r"\AC[0-9]+\Z", c)`
- Verified: `to_rgba("C0")` returns `(0.121..., 0.466..., 0.705..., 1.0)` - actual RGBA tuple

**Edit sites:**
- `lib/matplotlib/stackplot.py:9-11` - Add imports: `import itertools` and `from matplotlib import colors`  
- `lib/matplotlib/stackplot.py:70-74` - Replace prop_cycle modification with local color iterator creation
- `lib/matplotlib/stackplot.py:118` - Replace `axes._get_lines.get_next_color()` with `next(color_iter)`
- `lib/matplotlib/stackplot.py:124` - Replace `axes._get_lines.get_next_color()` with `next(color_iter)`

## Gate Loop: Iteration 1

**Approach**: Removed `axes.set_prop_cycle(color=colors)` call and replaced with `colors = itertools.cycle(colors)` to create a local color iterator. Changed both color assignment calls from `axes._get_lines.get_next_color()` to `next(colors) if colors is not None else axes._get_lines.get_next_color()`.

**codex feedback before gating**: 
- Original draft overcorrected by converting colors to RGBA - unnecessary since `fill_between` already handles CN references
- Original draft broke default color cycle behavior by not advancing the axes cycler when `colors=None`
- Suggested simpler fix: just cycle through colors list directly without resolving CN references

**Gate result**: ✅ PASS
- `lib/matplotlib/tests/test_axes.py::test_stackplot[png]` PASSED
- `lib/matplotlib/tests/test_axes.py::test_stackplot[pdf]` PASSED

**Trajectory**: Convergent (success on first iteration)

**Changes made**:
1. Added `import itertools` to imports
2. Replaced `axes.set_prop_cycle(color=colors)` with `colors = itertools.cycle(colors)`
3. Replaced `color = axes._get_lines.get_next_color()` (2 locations) with `color = next(colors) if colors is not None else axes._get_lines.get_next_color()`

This fix:
- Resolves CN color references by letting `fill_between` handle them directly (it already supports CN refs)
- Avoids putting CN references into the property cycle (which the validator correctly rejects)
- Preserves default behavior when `colors=None` by still calling `axes._get_lines.get_next_color()`
- Does NOT modify the axes cycler, satisfying the requirement "stackplot should not change Axes cycler"

---

# Audit: matplotlib__matplotlib-24026

## Patch verification

```
 lib/matplotlib/stackplot.py | 7 ++++---
 1 file changed, 4 insertions(+), 3 deletions(-)
```

Patch is live in the container.

## FAIL_TO_PASS

- `lib/matplotlib/tests/test_axes.py::test_stackplot[png]`: **PASS** ✅
- `lib/matplotlib/tests/test_axes.py::test_stackplot[pdf]`: **PASS** ✅

Both required tests now pass.

## PASS_TO_PASS regressions

**None.** Gate output shows 767 passed, 64 skipped, 0 failed. All tests that passed on base continue to pass.

## Pre-existing failures (not counted)

**None.** The fail-on-base capture showed all tests passing, and the gate confirms all tests still pass.

## Verdict analysis

✅ **All FAIL_TO_PASS tests pass**: Both `test_stackplot[png]` and `test_stackplot[pdf]` now pass.  
✅ **Zero PASS_TO_PASS regressions**: Full suite shows 767 passed with no failures.  
✅ **Contract satisfied**: Fix resolves the CN color reference issue without breaking existing functionality.

The patch successfully:
1. Fixes the ValueError with CN color references in stackplot
2. Stops stackplot from modifying the axes property cycle
3. Preserves default color cycling behavior when colors=None
4. Introduces zero regressions across the full test suite

VERDICT: RESOLVED
RE-ENTER: none
