# Hypothesis graph: matplotlib__matplotlib-24870

## H0: Initial failure observation (abduction, 60%)

**Hypothesis:** The tests fail because boolean arrays passed to `contour()`, `contourf()`, `tricontour()`, and `tricontourf()` are converted to float64 (0.0 and 1.0) but still use the default 7 levels, resulting in levels like [0.0, 0.15, 0.3, 0.45, 0.6, 0.75, 0.9, 1.05] instead of the expected [0.5] for line contours or [0, 0.5, 1] for filled contours.

**Evidence:**
- Test failure shows: `assert [0.0, 0.15000...00000001, ...] == [0.5]`
- Expected behavior: boolean inputs should auto-detect and default to levels=[0.5] for contour, levels=[0, 0.5, 1] for contourf

**Status:** Confirmed by test output

## H1: Root cause - missing boolean detection (deduction, 95%)

**Hypothesis:** The contour plotting code lacks boolean array detection logic. When z arrays are processed, they are immediately converted to float64 before any dtype checking occurs, losing the information that the original input was boolean.

**Code path:**
1. `pyplot.contour()` → `gca().contour()` → `QuadContourSet.__init__()` → `_process_args()` → `_contour_args()`
2. In `QuadContourSet._contour_args()` (lib/matplotlib/contour.py:1442-1465):
   - Line 1449: `z = ma.asarray(args[0], dtype=np.float64)` - boolean info lost here
   - Line 1452: or `z = self._check_xyz(args[:3], kwargs)` which also converts to float64 at line 1489
   - Line 1465: `self._process_contour_level_args(args)` - uses default 7 levels if not specified
3. Similar path for TriContourSet in lib/matplotlib/tri/_tricontour.py:53-76

**Evidence:**
- `lib/matplotlib/contour.py:1449` - `z = ma.asarray(args[0], dtype=np.float64)` converts before checking dtype
- `lib/matplotlib/contour.py:1489` - `z = ma.asarray(args[2], dtype=np.float64)` same issue
- `lib/matplotlib/contour.py:1123` - default levels_arg is 7 when not specified
- `lib/matplotlib/tri/_tricontour.py:57` - `z = np.ma.asarray(args[0])` preserves dtype initially but no boolean check follows

**Confidence:** 95% (deduction) - traced code path, confirmed conversion happens before detection could occur

## Edit sites

### Site 1: QuadContourSet._contour_args (lib/matplotlib/contour.py:1442-1465)

Need to:
1. Check if the original z input (args[0] for nargs<=2, args[2] for nargs<=4) is boolean before conversion
2. If boolean and self.levels is None, set self.levels to [0.5] for line contours or [0, 0.5, 1] for filled contours
3. Then proceed with existing float64 conversion

### Site 2: TriContourSet._contour_args (lib/matplotlib/tri/_tricontour.py:53-76)

Need to:
1. Check if args[0] is boolean after line 57 but before conversion operations
2. If boolean and self.levels is None, set self.levels to [0.5] for line contours or [0, 0.5, 1] for filled contours


## Gate Loop - /craft

**Iteration 1: Initial fix**

**Hypothesis**: Boolean arrays are converted to float64 before dtype detection, losing the boolean type information. Need to detect boolean dtype BEFORE conversion and set appropriate default levels.

**Edit sites**:
1. `lib/matplotlib/contour.py` QuadContourSet._contour_args: Added boolean detection before float64 conversion for both nargs <= 2 and nargs <= 4 cases
2. `lib/matplotlib/tri/_tricontour.py` TriContourSet._contour_args: Added boolean detection after z assignment

**Implementation**:
- For QuadContourSet: Check `ma.asarray(args[0]).dtype == bool` (nargs <= 2) or `ma.asarray(args[2]).dtype == bool` (nargs <= 4) before float64 conversion
- For TriContourSet: Check `z.dtype == bool` after `z = np.ma.asarray(args[0])`
- If boolean and `self.levels is None`, set levels to `[0.5]` for line contours or `[0, 0.5, 1]` for filled contours

**Gate result**: ✅ PASS
- test_bool_autolevel: PASSED
- All 66 tests passed, 1 skipped
- No regressions

**Outcome**: RESOLVED — FAIL_TO_PASS test passes, no PASS_TO_PASS regressions

---

# Audit: matplotlib__matplotlib-24870

## FAIL_TO_PASS
- lib/matplotlib/tests/test_contour.py::test_bool_autolevel: **PASS** ✓

## PASS_TO_PASS regressions
None - all 66 tests passed, 1 skipped

## Pre-existing (not counted, confirmed against base capture)
None - test_bool_autolevel was the only failure on base, now resolved

## Verification
Gate output shows all tests passing:
- 66 passed, 1 skipped
- test_bool_autolevel successfully passes with the fix
- No new failures introduced
- All PASS_TO_PASS tests remain passing

VERDICT: RESOLVED
RE-ENTER: none
