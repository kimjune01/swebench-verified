# Hypothesis graph: matplotlib__matplotlib-24570

## Hypothesis H0 (abduction)
**Status**: Initial diagnosis
**Timestamp**: 2026-05-23 recon phase

The tests fail because the `align` parameter logic in `_get_aligned_offsets()` has "top" and "bottom" reversed (and similarly "left" and "right").

**Evidence**:
- Test failure for `align="bottom"`: expects y_offset=0 for smaller box, gets y_offset=30
- Test failure for `align="top"`: expects y_offset=30 for smaller box, gets y_offset=0
- The behaviors are exactly swapped

**Code location**: `lib/matplotlib/offsetbox.py:169-174`

Current (incorrect) logic:
```python
elif align in ["left", "top"]:
    offsets = [d for h, d in hd_list]          # produces 0
elif align in ["right", "bottom"]:
    offsets = [height - h + d for h, d in hd_list]  # produces height-h
```

For HPacker with bottom alignment, smaller boxes should get offset=0 (stay at bottom).
For HPacker with top alignment, smaller boxes should get offset=(height-h) to push up.

Current code does the opposite.

**Root cause**: Lines 169 and 172 have the alignment values swapped.

**Confidence**: Deduction — 98% (traced through test expectations, coordinate system, and implementation)


## Craft gate loop — matplotlib__matplotlib-24570

### Iteration 1: Applied recon fix

**Changes:**
- `lib/matplotlib/offsetbox.py` line 169: `["left", "top"]` → `["left", "bottom"]`
- `lib/matplotlib/offsetbox.py` line 172: `["right", "bottom"]` → `["right", "top"]`

**Codex pre-gate volley:** Confirmed fix is correct. Noted missing regression coverage and nonzero descent testing, but those are outside /craft scope.

**Gate result:** ✓ PASS
- All 277 tests passed
- Both FAIL_TO_PASS tests now pass:
  - `test_packers[bottom]` ✓
  - `test_packers[top]` ✓
- No regressions

**Trajectory:** Resolution in 1 iteration.

**Root cause confirmed:** The alignment groupings in `_get_aligned_offsets()` were reversed. Swapping `["left", "top"]` ↔ `["left", "bottom"]` and `["right", "bottom"]` ↔ `["right", "top"]` fixed the inverted offset calculations for HPacker and VPacker.

## Audit — matplotlib__matplotlib-24570

**Timestamp**: 2026-05-23 audit phase

### Phase 1: Patch verification
✓ Patch is live in working tree:
```
lib/matplotlib/offsetbox.py | 4 ++--
1 file changed, 2 insertions(+), 2 deletions(-)
```

### Phase 2: Gate execution
Ran full gate: 277 passed, 1 skipped (SVG test — Inkscape not installed, expected)

### Phase 3: Classification

#### FAIL_TO_PASS (target tests — must pass)
- `lib/matplotlib/tests/test_offsetbox.py::test_packers[bottom]`: **PASS** ✓
- `lib/matplotlib/tests/test_offsetbox.py::test_packers[top]`: **PASS** ✓

#### PASS_TO_PASS regressions
**None** — all 275 PASS_TO_PASS tests still passing.

#### Pre-existing failures (not counted)
**None** — baseline had all tests passing except the two FAIL_TO_PASS tests.

### Phase 4: Verdict

**Contract fulfilled:**
- All FAIL_TO_PASS tests now pass ✓
- Zero PASS_TO_PASS regressions ✓

**Patch summary:**
Lines 169 and 172 of `lib/matplotlib/offsetbox.py` swapped "top"↔"bottom" in the align groupings:
- Line 169: `["left", "top"]` → `["left", "bottom"]`
- Line 172: `["right", "bottom"]` → `["right", "top"]`

This corrects the inverted offset calculations in `_get_aligned_offsets()` for HPacker and VPacker alignment modes.

**Kill report**: N/A (resolved)

VERDICT: RESOLVED
RE-ENTER: none
