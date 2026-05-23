# Hypothesis graph: matplotlib__matplotlib-24970

## H₀: Initial observation (abduction)
The test `test_index_dtype[uint8]` fails with DeprecationWarning when calling a colormap with uint8 input. NumPy 1.24+ warns that assignment of out-of-bound Python integers (256, 257, 258) to uint8 arrays will fail in future versions.

**Evidence:**
- `lib/matplotlib/colors.py:730`: `xa[xa > self.N - 1] = self._i_over` assigns 257 to uint8 array
- `lib/matplotlib/colors.py:731`: `xa[xa < 0] = self._i_under` assigns 256 to uint8 array  
- `lib/matplotlib/colors.py:732`: `xa[mask_bad] = self._i_bad` assigns 258 to uint8 array

## H₁: Root cause (deduction)
The `Colormap.__call__` method uses sentinel values (self._i_under=N, self._i_over=N+1, self._i_bad=N+2) as special indices into the lookup table. For typical colormaps with N=256, these values are 256, 257, 258.

When the input array `xa` has dtype uint8, it cannot represent these values (uint8 range is 0-255). Direct assignment triggers NumPy deprecation warnings and will fail in future NumPy versions.

**Call path:**
1. `cm(np.uint8(0))` → `Colormap.__call__`
2. Line 711: `xa = np.array(X, copy=True)` preserves uint8 dtype
3. Line 716: float conversion block is skipped (xa is integer type)
4. Lines 730-732: sentinel values assigned to uint8 array → DeprecationWarning

**Supporting evidence:**
- `lib/matplotlib/colors.py:673-675`: Sentinel values defined as N, N+1, N+2
- `lib/matplotlib/colors.py:727`: Float inputs are converted to `int` (int64) before use
- `lib/matplotlib/colors.py:2021`: Similar pattern elsewhere uses explicit int16 conversion for sentinel values
- Test comment: "We use subtraction in the indexing, so need to verify that uint8 works"

**Confidence:** Deduction — 98%

## H₁: Fix specification
Before assigning sentinel values (lines 730-732), ensure `xa` has a dtype capable of representing values up to self._i_bad (N+2).

**Edit site:**
- `lib/matplotlib/colors.py` lines 728-729 (between float conversion and sentinel assignment):
  - Check if xa has integer dtype that cannot hold sentinel values
  - If so, convert xa to a dtype that can (e.g., `int` to match line 727 pattern)

**Justification:**
- Matches existing pattern at line 727 where float→int conversion uses `astype(int)`
- `int` gives int64 on modern systems, which can hold sentinel values
- NumPy's `take()` at line 737 works with any integer dtype
- Minimal change, affects only the code path that needs it


## Craft iteration 1: dtype conversion fix

**Hypothesis**: Integer dtypes that cannot represent sentinel values (256-258) need to be widened to `int` before sentinel assignment.

**Implementation**: Added check after line 727 in `lib/matplotlib/colors.py`:
```python
# Ensure integer types can represent sentinel values (N, N+1, N+2)
if xa.dtype.kind in 'iu':
    if np.iinfo(xa.dtype).max < self._i_bad:
        xa = xa.astype(int)
```

**Codex pre-gate review**: Structural analysis clean. Confirmed logic prevents out-of-bound assignments by widening uint8 (max 255) to int64 before assigning sentinels (256-258).

**Gate result**: PASS
- `test_index_dtype[uint8]`: ✅ PASSED (FAIL_TO_PASS resolved)
- Unrelated failure in `test_double_register_builtin_cmap`: pre-existing warning type mismatch in colormap registration, confirmed unrelated to dtype conversion in `__call__`

**Evidence trajectory**: Convergent → RESOLVED

**Confidence**: 100% — FAIL_TO_PASS test passes, codex confirmed no behavioral regression, unrelated gate failure independently verified.


# Audit: matplotlib__matplotlib-24970

## FAIL_TO_PASS
- test_index_dtype[uint8]: PASS ✓

## PASS_TO_PASS regressions
none

## Pre-existing (not counted, confirmed against base capture)
- test_double_register_builtin_cmap: Already failing on base (baseline line 121). Expects UserWarning but receives MatplotlibDeprecationWarning in cm.register_cmap call. Completely unrelated to dtype conversion fix in Colormap.__call__.

## Kill report
Not applicable — fix is RESOLVED.

VERDICT: RESOLVED
RE-ENTER: none
