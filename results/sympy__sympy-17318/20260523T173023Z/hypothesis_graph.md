# Hypothesis graph: sympy__sympy-17318

## Hypothesis Node 1 (Initial Diagnosis)
**Status:** Active  
**Mode:** Deduction  
**Confidence:** 95%

### Observation
Test `test_issue_12420` fails with `IndexError: tuple index out of range` at `sympy/simplify/radsimp.py:1116` in function `_split_gcd` when calling `g = a[0]`.

Stack trace:
```
_sqrt_match (sqrtdenest.py:160) 
  -> split_surds(p) 
  -> _split_gcd(*surds) (radsimp.py:1080)
  -> g = a[0] (radsimp.py:1116) raises IndexError
```

### Root Cause
The function `_split_gcd(*a)` assumes it receives at least one argument but fails when called with zero arguments. This happens when:

1. `_sqrt_match(4 + I)` is called
2. The expression `4 + I` is an `Add` type
3. The condition `all((x**2).is_Rational for x in pargs)` evaluates to True because both `4**2 = 16` and `I**2 = -1` are rational
4. This triggers the early return path via `split_surds(p)` at line 160
5. In `split_surds`, the line `surds = [x[1]**2 for x in coeff_muls if x[1].is_Pow]` produces an empty list because neither `4` nor `I` is a `Pow` expression (no square roots)
6. `_split_gcd(*surds)` expands to `_split_gcd()` with no arguments
7. Line 1116 tries to access `a[0]` on an empty tuple, raising `IndexError`

### Evidence
- `sympy/simplify/radsimp.py:1116` - `g = a[0]` with no guard for empty input
- `sympy/simplify/radsimp.py:1077` - `surds = [x[1]**2 for x in coeff_muls if x[1].is_Pow]` can be empty
- `sympy/simplify/radsimp.py:1080` - `_split_gcd(*surds)` called without checking if surds is empty
- Test expectation: `_sqrt_match(4 + I) == []` should return empty list, not raise exception

### Predicted Fix
Add empty input handling to `_split_gcd` at the start of the function. When called with no arguments, return `(1, [], [])` where:
- `g = 1` (multiplicative identity, the gcd of an empty set)
- `b1 = []` (no elements with the gcd)
- `b2 = []` (no elements coprime to the gcd)

### Edit Sites
- `sympy/simplify/radsimp.py` lines 1103-1124: Add guard at beginning of `_split_gcd` to handle empty input

## Gate Iteration 1
**Status:** Divergent (progress)  
**Gate result:** AssertionError (not IndexError)

### Changes Applied
Added empty-input guard to `_split_gcd`:
```python
if not a:
    return (1, [], [])
```

### Gate Output
```
test_issue_12420 F
AssertionError at line 187: assert _sqrt_match(4 + I) == []
```

### Analysis
The crash is fixed (no more IndexError), but `_sqrt_match(4 + I)` now returns `[4+I, 0, 1]` instead of the expected `[]`. This is progress — we moved from a crash to wrong output.

**Root cause refinement:** The condition `all((x**2).is_Rational for x in pargs)` in `_sqrt_match` is too broad. It matches `4 + I` even though there are no square roots present. When `split_surds(4 + I)` is called:
- `surds = []` (no Pow expressions)
- `_split_gcd()` returns `(1, [], [])`
- Final result is `(1, 0, 4+I)` 
- `_sqrt_match` returns `[4+I, 0, 1]` but should return `[]`

**Next action:** Add a pre-check in `_sqrt_match` to verify surds actually exist before calling `split_surds`.

## Gate Iteration 2  
**Status:** Green (resolved)  
**Gate result:** All tests passed

### Changes Applied (codex-guided)
1. **radsimp.py**: Empty-input guard in `_split_gcd` (from iteration 1)
2. **sqrtdenest.py**: Added surd-existence check in `_sqrt_match` before calling `split_surds`:
```python
coeff_muls = [x.as_coeff_Mul() for x in pargs]
surds = [s for c, s in coeff_muls if s.is_Pow and s.exp == S.Half]
if surds and all((x**2).is_Rational for x in pargs):
    r, b, a = split_surds(p)
    res = a, b, r
    return list(res)
```

### Gate Output
```
test_issue_12420 ok
============ tests finished: 12 passed, 1 skipped, in 7.85 seconds =============
```

### Manual Verification
```python
_sqrt_match(4 + I) = []              # ✓ Correct (no surds)
_sqrt_match(1 + sqrt(2)) = [1, 1, 2] # ✓ Correct (has surds)
_sqrt_match(1 + I*sqrt(2)) = [1, I, 2] # ✓ Correct (complex coeff with surds)
sqrtdenest((3 - sqrt(2)*sqrt(4 + 3*I) + 3*I)/2) = I # ✓ Correct
```

### Resolution
The fix required two coordinated changes:
1. **Defense in depth**: Guard `_split_gcd` against empty input to prevent crashes
2. **Upstream correction**: Check for actual surd presence in `_sqrt_match` before taking the `split_surds` path

The condition `all((x**2).is_Rational for x in pargs)` was originally intended to detect expressions containing square roots (where squaring eliminates the radical), but it incorrectly matched expressions like `4 + I` where terms are already rational without any radicals. The new check `surds and all(...)` ensures we only call `split_surds` when square roots are actually present.

---

# Audit: sympy__sympy-17318

## FAIL_TO_PASS
- test_issue_12420: **PASS** ✓

## PASS_TO_PASS regressions
**None** — all 10 PASS_TO_PASS tests passed:
- test_sqrtdenest: ok ✓
- test_sqrtdenest2: ok ✓
- test_sqrtdenest_rec: ok ✓
- test_issue_6241: ok ✓
- test_sqrtdenest3: ok ✓
- test_sqrtdenest4: ok ✓
- test_sqrt_symbolic_denest: ok ✓
- test_issue_5857: ok ✓
- test_subsets: ok ✓
- test_issue_5653: ok ✓

## Pre-existing (not counted)
**None** — no failures detected in gate output.

## Gate Output Summary
```
============ tests finished: 12 passed, 1 skipped, in 7.76 seconds =============
```

## Classification
The craft patch successfully fixed the IndexError crash in `test_issue_12420` while introducing zero regressions. Both components of the fix (the `_split_gcd` empty-input guard and the surd-existence check in `_sqrt_match`) are working correctly.

VERDICT: RESOLVED
RE-ENTER: none
