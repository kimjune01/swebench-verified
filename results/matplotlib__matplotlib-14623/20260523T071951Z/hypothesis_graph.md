# Hypothesis graph: matplotlib__matplotlib-14623

## H0: Failure mode (abduction)
**Status**: Initial observation
**Confidence**: 99% (deduction - read stack trace)

The test `test_inverted_limits` fails because:
- Setting `ax.set_ylim(10, 1)` on a log-scale axis returns `(1.0, 10.0)` instead of `(10, 1)`
- The limits are being auto-sorted into increasing order
- Expected behavior: limits should preserve inverted order like linear axes do

**Evidence**:
```
AssertionError: assert (1.0, 10.0) == (10, 1)
```

## H1: Root cause - LogLocator.nonsingular forces increasing order (deduction)
**Status**: Confirmed via code reading
**Confidence**: 95% (deduction - traced call chain and read implementation)

**Call chain**:
1. `set_ylim(10, 1)` in `lib/matplotlib/axes/_base.py:3540`
2. Line ~3646: `bottom, top = self.yaxis.get_major_locator().nonsingular(bottom, top)`
3. For log scale, major locator is `LogLocator`
4. `LogLocator.nonsingular` in `lib/matplotlib/ticker.py:2378-2397`

**The bug**:
```python
# lib/matplotlib/ticker.py:2381-2383
if vmin > vmax:
    vmin, vmax = vmax, vmin
```

LogLocator unconditionally swaps the values to force increasing order.

**Contrast with base class**:
```python
# lib/matplotlib/ticker.py:1523-1524
def nonsingular(self, v0, v1):
    return mtransforms.nonsingular(v0, v1, increasing=False, expander=.05)
```

The base `Locator.nonsingular` passes `increasing=False`, which preserves inverted order.

**Supporting evidence**:
- `lib/matplotlib/ticker.py:1523` - Base Locator preserves order with `increasing=False`
- `lib/matplotlib/ticker.py:2381-2383` - LogLocator forces swap
- `lib/matplotlib/ticker.py:2627-2628` - LogitLocator has identical bug
- `lib/matplotlib/axes/_base.py:3267` - set_xlim has identical call pattern (affects x-axis too)


## Craft Gate Loop

### Iteration 1: Initial Implementation
**Hypothesis**: Fix LogLocator and LogitLocator to preserve inverted order by remembering swap state and restoring original order before return.

**Changes applied**:
- `lib/matplotlib/ticker.py` LogLocator.nonsingular: Added `swapped` flag, restore order if inverted
- `lib/matplotlib/ticker.py` LogitLocator.nonsingular: Same fix, with special handling for singular case

**Gate result**: 
- **FAIL_TO_PASS test (test_inverted_limits): PASSED ✓**
- Gate shows 180 other test failures, but investigation reveals:
  - All failures are image comparison failures
  - Root cause: FreeType version mismatch (expected 2.6.1, found 2.11.1)  - Gate output header states: "Expect many image comparison failures"
  - Our changes only affect LogLocator/LogitLocator (log/logit scales)
  - Failing tests are mostly linear scale tests (e.g., test_square_plot)
  - Codex analysis confirms: our changes cannot affect linear scale tests
  
**Verification**:
```python
fig, ax = plt.subplots()
ax.set_yscale("log")
ax.set_ylim(10, 1)
assert ax.get_ylim() == (10, 1)  # ✓ PASSES
```

**Conclusion**: Fix is correct. FAIL_TO_PASS test passes. Other failures are pre-existing environmental issues.

**Evidence classification**: Convergent - target behavior achieved, other failures are unrelated baseline issues.

## Audit: matplotlib__matplotlib-14623

### Phase 1: Patch verification
```
lib/matplotlib/ticker.py | 18 ++++++++++++++++--
1 file changed, 16 insertions(+), 2 deletions(-)
```
Patch is live in the tree.

### Phase 2: Gate execution
Full gate run completed:
- 401 tests PASSED
- 180 tests FAILED
- 73 skipped
- Runtime: 38.24s

### Phase 3: Classification

#### FAIL_TO_PASS
- `test_inverted_limits`: **PASSED** ✓

#### PASS_TO_PASS regressions
None. All 180 failures match the fail-on-base capture exactly:
- `test_canonical[png]`, `test_canonical[pdf]` - pre-existing
- `test_arc_ellipse[pdf]` - pre-existing
- `test_markevery[png]`, `test_markevery[pdf]` - pre-existing
- `test_markevery_line[png]`, `test_markevery_line[pdf]` - pre-existing
- `test_markevery_linear_scales[pdf]` - pre-existing
- `test_markevery_linear_scales_zoomed[pdf]` - pre-existing
- `test_markevery_log_scales[pdf]` - pre-existing
- `test_markevery_polar[png]`, `test_markevery_polar[pdf]` - pre-existing
- ... (all 180 failures confirmed against fail-on-base)

Spot-checked PASS_TO_PASS tests:
- `test_get_labels`: PASSED ✓
- `test_inverted_cla`: PASSED ✓
- `test_autoscale_tight`: PASSED ✓
- `test_use_sticky_edges`: PASSED ✓

#### Pre-existing failures (not counted)
All 180 gate failures were present in the fail-on-base capture. FreeType version mismatch (2.6.1 expected, 2.11.1 found) causes image comparison failures unrelated to the LogLocator/LogitLocator fix.

### Phase 4: Verdict

**Contract fulfilled:**
- ✓ All FAIL_TO_PASS tests now pass (1/1)
- ✓ Zero PASS_TO_PASS regressions

**Patch summary:**
The fix correctly preserves inverted axis order for log and logit scales by:
1. Remembering the original order (`swapped` flag)
2. Performing necessary computations with normalized order
3. Restoring the original order before return

This matches the behavior of the base `Locator.nonsingular` which uses `increasing=False`.

VERDICT: RESOLVED
RE-ENTER: none
