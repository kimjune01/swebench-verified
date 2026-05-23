# Hypothesis Graph: matplotlib__matplotlib-24637

## H₀ (Initial): AnnotationBbox.draw missing gid group wrapper
**Type**: abduction
**Status**: active
**Confidence**: 95% (deduction - code inspection)

The test fails because AnnotationBbox.draw() does not wrap its rendering with renderer.open_group()/close_group() calls to emit the gid attribute to the SVG output.

**Evidence**:
- Test expects: `<g id="a test for issue 20044">` in SVG output
- Test fails: assertion error - string not found in output
- `lib/matplotlib/offsetbox.py:1449-1464`: AnnotationBbox.draw() has no open_group/close_group calls
- `lib/matplotlib/text.py:749,810`: Text.draw() properly uses renderer.open_group('text', self.get_gid()) ... renderer.close_group('text')
- `lib/matplotlib/legend.py:649,669`: Legend.draw() properly uses renderer.open_group('legend', gid=self.get_gid()) ... renderer.close_group('legend')
- Pattern confirmed across multiple artists: axes, axis, collections, figure, lines, patches, table

**Edit sites**:
- `lib/matplotlib/offsetbox.py` lines 1449-1464: AnnotationBbox.draw() method must add:
  - `renderer.open_group('annotation', gid=self.get_gid())` after visibility check
  - `renderer.close_group('annotation')` before `self.stale = False`

## Craft gate iteration 1

**Patch applied:**
- Added `renderer.open_group(self.__class__.__name__, gid=self.get_gid())` after visibility check in AnnotationBbox.draw()
- Added `renderer.close_group(self.__class__.__name__)` before `self.stale = False`

**codex feedback (pre-gate):**
- Changed group name from hardcoded `'annotation'` to `self.__class__.__name__` to match matplotlib's pattern
- Confirmed no behavioral break for normal rendering
- Confirmed early return prevents unbalanced close on invisible/out-of-bounds artists

**Gate result:** ✅ PASS
- test_annotationbbox_gid: PASSED
- All 31 tests passed, 19 skipped
- FAIL_TO_PASS requirement satisfied

**E-value trajectory:** Convergent (success) — test now passes after applying the open_group/close_group wrapper pattern

**Resolution:** The fix correctly implements the standard matplotlib pattern for emitting gid attributes to SVG output. AnnotationBbox.draw() now wraps its rendering operations with renderer group calls, allowing the gid set via set_gid() to appear in the SVG output.

## Audit: matplotlib__matplotlib-24637

### Patch verification
```
lib/matplotlib/offsetbox.py | 2 ++
1 file changed, 2 insertions(+)
```

### FAIL_TO_PASS
- lib/matplotlib/tests/test_backend_svg.py::test_annotationbbox_gid: **PASS** ✓

### PASS_TO_PASS regressions
None - all 30 PASS_TO_PASS tests remain passing.

### Pre-existing failures
None - all tests in gate either passed or were skipped (19 skipped due to Inkscape/font dependencies, as expected on base).

### Gate output summary
- 31 passed, 19 skipped
- test_annotationbbox_gid transitioned from FAIL → PASS
- Zero regressions introduced
- Full contract satisfied
