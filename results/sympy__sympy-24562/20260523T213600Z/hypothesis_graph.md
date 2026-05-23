# Hypothesis graph: sympy__sympy-24562

## H₀: String multiplication bug (abduction)

The tests fail because `Rational(p, q)` performs string multiplication when p or q are strings.

When `Rational('0.5', '100')` is called, the code converts `p='0.5'` to `Rational(1, 2)` but then multiplies `q` (still the string `'100'`) by `p.q` (the integer `2`). In Python, `'100' * 2 = '100100'` (string repetition), resulting in denominator `100100` instead of `200`.

**Evidence:**
- Line 1629: `q *= p.q` occurs before `q` is converted from string
- String multiplication: `'100' * 2 = '100100'`
- String multiplication: `'1.5' * 2 = '1.51.5'` (matches error message)

**Root cause:** Commit 44f22e62e0 (Aug 2021) restructured the Rational constructor to convert p and q separately, but performs multiplication before ensuring q is numeric.

**Fix:** Convert both p and q to Rational/int before performing any cross-multiplication.


## Craft Gate Loop

### Iteration 1: Initial Fix

**Diagnosis:** Recon correctly identified that the bug occurs when `q *= p.q` is executed while q is still a string, causing string repetition (e.g., `'100' * 2 = '100100'`).

**Fix Applied:** Modified `sympy/core/numbers.py` lines 1628-1641 to:
1. Convert both p and q to their proper types (Rational or int) first
2. Extract denominators (p_q, q_q) during conversion
3. Cross-multiply after both conversions complete

```python
# Before: buggy sequential conversion with premature multiplication
if not isinstance(p, SYMPY_INTS):
    p = Rational(p)
    q *= p.q  # BUG: q might still be string here
    p = p.p

# After: extract denominators, then cross-multiply
if not isinstance(p, SYMPY_INTS):
    p = Rational(p)
    p, p_q = p.p, p.q
else:
    p = int(p)
    p_q = 1

# Same pattern for q...

p *= q_q
q *= p_q
```

**Volley with codex:** Confirmed the fix logic is correct. codex suggested the cleaner extraction pattern (p, p_q = p.p, p.q) instead of nested isinstance checks, which was adopted.

**Gate Result:** ✅ PASS
- test_issue_24543: ok
- All 107 tests passed, 1 skipped, 1 expected to fail

**Trajectory:** Convergent success — FAIL_TO_PASS test now passes on first gate run.


---

# Audit: sympy__sympy-24562

## FAIL_TO_PASS
- test_issue_24543: PASS ✓

## PASS_TO_PASS regressions
none

## Pre-existing (not counted, confirmed against base capture)
- test_mpmath_issues: expected to fail (same as baseline)
- test_numpy_to_float: skipped (same as baseline)

## Summary
The craft patch successfully fixes the issue. The problem was in `Rational.__new__()` where converting both `p` and `q` from non-SYMPY_INTS would overwrite values before they could be used. The fix extracts both the numerator and denominator values before performing cross-multiplication, ensuring `Rational(float, float)` works correctly.

All 107 applicable tests pass with no regressions.

