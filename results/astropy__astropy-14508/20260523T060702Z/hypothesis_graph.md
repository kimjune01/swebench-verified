# Hypothesis graph: astropy__astropy-14508

## H₀: Baseline observation (abduction)
**Status**: CONFIRMED → leads to H₁

The test `test_floating_point_string_representation_card` fails because:
- Creating `fits.Card(k, 0.009125, com)` triggers a VerifyWarning: "Card is too long, comment will be truncated"
- The card uses "0.009124999999999999" (20 chars) instead of "0.009125" (8 chars)
- This forces comment truncation when the shorter representation would fit

**Evidence**:
```
> assert str(c)[: len(expected_str)] == expected_str
E astropy.io.fits.verify.VerifyWarning: Card is too long, comment will be truncated.
```

Trace: Card.__str__() → Card.image → Card._format_image() → Card._format_value() → _format_value() → _format_float()

## H₁: Root cause in _format_float (deduction)
**Status**: ACTIVE
**Confidence**: 95% (deduction - traced through code)

The `_format_float()` function at `astropy/io/fits/card.py:1300-1329` always uses `f"{value:.16G}"` format, which produces unnecessarily long representations with 16 significant digits.

**Evidence**:
- `card.py:1302`: `value_str = f"{value:.16G}"` 
- For 0.009125: `.16G` → "0.009124999999999999" (20 chars) vs `str()` → "0.009125" (8 chars)
- For 8.95: `.16G` → "8.949999999999999" (17 chars) vs `str()` → "8.95" (4 chars)
- For -99.9: `.16G` → "-99.90000000000001" (18 chars) vs `str()` → "-99.9" (5 chars)

**Why this is wrong**:
Python's `str()` representation is often shorter and more accurate for values that can be represented exactly in decimal (like 0.009125). The .16G format is designed for maximum precision but produces binary floating-point artifacts.

**What needs to change**:
The `_format_float()` function should try `str(value)` first and only fall back to `.16G` if:
1. The `str()` representation exceeds 20 characters, OR  
2. Special normalization is needed

This preserves FITS requirements (decimal point, uppercase E notation, 2-digit exponents) while using the shortest accurate representation.


## Gate Loop - Iteration 1

**Fix applied**: Modified `_format_float()` in `astropy/io/fits/card.py`:
1. Added `math.isfinite()` check to handle non-finite values (NAN, INF) first
2. Changed primary formatting from `.16G` to `str(value)` for shorter representations
3. Fall back to `.16G` only when `str(value)` exceeds 20 characters
4. Added `.upper()` to normalize lowercase `e` to uppercase `E` for scientific notation

**Codex review**: Caught two critical issues before first gate run:
1. Lowercase `e` in scientific notation would not be recognized by existing logic
2. Non-finite values (nan, inf) would get `.0` appended (e.g., `nan.0`)

**Gate result**: ✅ **PASSED**
- `test_floating_point_string_representation_card`: **PASSED**
- All 175 tests in test_header.py: **PASSED**

**Trajectory**: Convergent success on first iteration after codex review.

## Audit: astropy__astropy-14508

**Patch status**: Live (15 insertions, 1 deletion in astropy/io/fits/card.py)

### FAIL_TO_PASS
- `astropy/io/fits/tests/test_header.py::TestHeaderFunctions::test_floating_point_string_representation_card`: **PASS** ✓

### PASS_TO_PASS regressions
None. All 175 tests in test_header.py passed without regression.

### Pre-existing failures (not counted)
None. Base capture showed all tests passing before the patch.

### Summary
The craft patch successfully resolved the issue:
- The target test now passes without triggering VerifyWarning
- Float values like 0.009125, 8.95, -99.9 now use shorter `str()` representations instead of verbose `.16G` format
- No regressions introduced in the test suite
- Clean gate: 175/175 tests passing

VERDICT: RESOLVED
RE-ENTER: none
