# Hypothesis graph: matplotlib__matplotlib-26466

## Hypothesis H0 (Initial diagnosis)
**Mode:** Deduction  
**Confidence:** 95%

### Failure summary
The test `test_annotate_and_offsetfrom_copy_input` creates annotations with numpy array inputs for the `xy` parameter (in `_AnnotationBase`) and `ref_coord` parameter (in `OffsetFrom`), then mutates those arrays. The test expects both figures to render identically, but they don't because the mutations affect the stored references.

The failure is an ImageComparisonFailure - the rendered images differ because the annotation positions change after the input arrays are mutated.

### Root cause
Both `OffsetFrom.__init__` and `_AnnotationBase.__init__` store direct references to input coordinate arrays instead of making defensive copies.

**Evidence:**
- `lib/matplotlib/text.py:1393` - `self._ref_coord = ref_coord` stores the reference directly
- `lib/matplotlib/text.py:1459` - `self.xy = xy` stores the reference directly

When the user later mutates the input array (e.g., `of_xy[:] = 1` or `an_xy[:] = 2`), the stored attributes reflect those changes. During rendering:
- `OffsetFrom.__call__` accesses `self._ref_coord` on lines 1433-1434, 1437-1439, 1443
- `_AnnotationBase._get_position_xy` accesses `self.xy` on line 1573

These accesses read the mutated values, causing the annotation to render at the wrong position.

### Edit sites
1. `lib/matplotlib/text.py` line 1393 (in `OffsetFrom.__init__`):
   - Change `self._ref_coord = ref_coord` to `self._ref_coord = tuple(ref_coord)`
   - Ensures immutable copy; all unpacking operations `xf, yf = self._ref_coord` still work

2. `lib/matplotlib/text.py` line 1459 (in `_AnnotationBase.__init__`):
   - Change `self.xy = xy` to `self.xy = tuple(xy)`
   - Ensures immutable copy; unpacking `x, y = xy` and indexing `xy[0]`, `xy[1]` still work

### Supporting evidence
- Line 1434, 1439: `xf, yf = self._ref_coord` - unpacking works with tuples
- Line 1443: `x, y = self._artist.transform(self._ref_coord)` - transform accepts tuples
- Line 1466: `x, y = xy` - unpacking works with tuples
- Line 1639: `self.xy[0]`, `self.xy[1]` - indexing works with tuples

Using `tuple()` conversion is the standard Python pattern for defensive copying of coordinate pairs.


## Gate Loop — Iteration 1

**Drafted fix**: Change both `OffsetFrom.__init__` and `_AnnotationBase.__init__` to unpack and reassign coordinate parameters:
- Line 1392: `x, y = ref_coord; self._ref_coord = x, y`
- Line 1459: `x, y = xy; self.xy = x, y`

**Codex volley**: Initial draft used `tuple(ref_coord)` and `tuple(xy)`. Codex correctly noted that unpacking is superior — it validates shape at init time and prevents bad inputs like `(1, 2, 3)` from being accepted.

**Revised fix**: Applied unpacking approach per codex recommendation.

**Gate result**: ✅ PASSED — all 104 tests passed, including `test_annotate_and_offsetfrom_copy_input[png]`.

**Trajectory**: Convergent-success on first iteration.

**Resolution**: The fix correctly addresses the root cause by making defensive copies of coordinate inputs while preserving all unpacking and indexing operations used throughout the codebase.

---

# Audit: matplotlib__matplotlib-26466

## FAIL_TO_PASS
- lib/matplotlib/tests/test_text.py::test_annotate_and_offsetfrom_copy_input[png]: **PASSED** ✓

## PASS_TO_PASS regressions
None - all 103 other tests in test_text.py passed.

## Pre-existing (not counted, confirmed against base capture)
None - all tests passed or were skipped (12 skipped svg tests due to missing Inkscape).

## Summary
The fix successfully resolves the issue. The FAIL_TO_PASS test now passes, confirming that `annotate()` and `OffsetFrom` properly handle mutable input arrays without being affected by subsequent mutations. All existing tests continue to pass with no regressions introduced.

**Gate output:**
- 104 tests passed
- 12 tests skipped (svg comparison tests - missing Inkscape)
- 0 tests failed
- Total run time: 4.04s

The patch ensures that when numpy arrays are passed as `xy` coordinates to `annotate()` or `ref_coord` to `OffsetFrom`, subsequent mutations to those arrays do not affect the created annotations.

VERDICT: RESOLVED
RE-ENTER: none
