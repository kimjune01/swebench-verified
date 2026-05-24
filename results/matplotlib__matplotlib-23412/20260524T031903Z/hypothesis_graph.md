# Hypothesis graph: matplotlib__matplotlib-23412

## H₁: Dash offset explicitly zeroed in Patch.draw (ACTIVE)

**Status**: Abduction (85% confidence)
**Date**: 2026-05-23

### Evidence
1. Test fails with image comparison (RMS 24.315) - test expects offset (6, [6, 6]) to produce different rendering than (0, [6, 6])
2. `lib/matplotlib/patches.py:426-429` - `set_linestyle()` correctly parses and stores dash offset in `_unscaled_dash_pattern` and `_dash_pattern`
3. `lib/matplotlib/patches.py:552` - `_bind_draw_path_function()` calls `gc.set_dashes(*self._dash_pattern)` which would pass the offset
4. **SMOKING GUN**: `lib/matplotlib/patches.py:590-591` - `draw()` method explicitly overrides `_dash_pattern` to `(0, self._dash_pattern[1])` before drawing, zeroing out the offset
5. Comment on line 589: "Patch has traditionally ignored the dashoffset."
6. Git history (commit 5c564d4007, 9c0fa9ed83) shows this was an intentional backwards-compatibility decision

### Root cause
The dash offset is correctly stored by `set_linestyle()` but is deliberately discarded in the `draw()` method using a context manager that temporarily sets the offset to 0.

### Edit sites
- `lib/matplotlib/patches.py` lines 590-591: Remove the `cbook._setattr_cm(self, _dash_pattern=(0, self._dash_pattern[1]))` context manager wrapper
- Simply use `self._bind_draw_path_function(renderer)` without the `_setattr_cm` override

### Confidence rationale
Deduction from code reading - the explicit zeroing is clearly visible in the source, and the test failure confirms the offset is not being applied. The only uncertainty is whether removing this will break something else (e.g., backwards compatibility with old code that relied on offsets being ignored).

## craft — gate iteration 1

**Edit applied:** Removed the `cbook._setattr_cm` context manager (lines 589-591 in `lib/matplotlib/patches.py`) that was zeroing the dash offset. Changed from:
```python
# Patch has traditionally ignored the dashoffset.
with cbook._setattr_cm(
         self, _dash_pattern=(0, self._dash_pattern[1])), \
     self._bind_draw_path_function(renderer) as draw_path:
```
to:
```python
with self._bind_draw_path_function(renderer) as draw_path:
```

**Gate result:** ✓ PASS — All 47 tests passed, including `test_dash_offset_patch_draw[png]`

**Verdict:** Recon diagnosis was correct. The dash offset was being deliberately zeroed for backwards compatibility, but the test requires it to work. Removing the override allows the offset stored in `_dash_pattern[0]` to pass through to the graphics context.

## audit — final verification

**Date**: 2026-05-23

### Phase 1: Patch confirmation
✓ Patch is live: 1 file changed, 1 insertion(+), 4 deletions(-) in `lib/matplotlib/patches.py`

### Phase 2: Gate execution
Full test suite run completed: 47 passed, 8 skipped (svg tests - platform limitation)

### Phase 3: Classification against baseline

#### FAIL_TO_PASS
- `test_dash_offset_patch_draw[png]`: **PASS** ✓ 
  - Baseline: FAILED with ImageComparisonFailure (RMS 24.315)
  - After patch: PASSED

#### PASS_TO_PASS regressions
None. All 46 PASS_TO_PASS tests remain passing.

#### Pre-existing failures
None applicable (all baseline failures were in FAIL_TO_PASS).

### Phase 4: Verdict

**FAIL_TO_PASS**: 1/1 passing (100%)
**Regressions**: 0/46 PASS_TO_PASS tests (0%)

The fix correctly removes the dash offset override in `Patch.draw()`, allowing the offset stored during `set_linestyle()` to flow through to the graphics context. No regressions introduced.

**VERDICT: RESOLVED**
**RE-ENTER: none**
