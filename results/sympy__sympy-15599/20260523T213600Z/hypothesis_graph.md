# Hypothesis graph: sympy__sympy-15599

## H₀: Initial observation (abduction)
The test `test_Mod` fails because `Mod(3*i, 2)` does not simplify to `Mod(i, 2)`. The assertion `assert Mod(3*i, 2) == Mod(i, 2)` raises AssertionError. The expression remains as `Mod(3*i, 2)` instead of being reduced.

**Evidence:**
- Test output: `AssertionError` at line 1667 of `sympy/core/tests/test_arit.py`
- Runtime check: `Mod(3*i, 2)` evaluates to `Mod(3*i, 2)` (unchanged)
- Expected: `Mod(i, 2)`

## H₁: Root cause - Mul simplification guard condition (deduction - 95%)

**Hypothesis:** The Mul simplification block in `sympy/core/mod.py` lines 126-140 only activates when the multiplication already contains Mod terms (`mod_l` is non-empty). For `Mod(3*i, 2)`, the argument `3*i` is a Mul with no Mod terms, so `mod_l = []` and the condition `if mod_l and all(...)` is False. The simplification that would reduce `Mod(3, 2) * Mod(i, 2)` to `Mod(i, 2)` is never attempted.

**Supporting evidence:**
- `sympy/core/mod.py:126` - condition `if mod_l and all(inner.args[1] == q for inner in mod_l):` requires `mod_l` to be non-empty
- Runtime trace: `(3*i).args = (3, i)`, neither is a Mod, so `mod_l = []` and `non_mod_l = [3, i]`
- `Mod(3, 2) = 1` (simplifies to a constant)
- `Mod(i, 2) = Mod(i, 2)` (stays symbolic)
- The transformation `[Mod(x, q) for x in non_mod_l]` would give `[1, Mod(i, 2)]`, which simplifies to `Mod(i, 2)`
- Comparison: `Mod(8*i, 4) = 0` works because `gcd(8*i, 4) = 4`, so GCD extraction handles it before the Mul block is reached
- `gcd(3*i, 2) = 1`, so no GCD extraction occurs for the failing case

**Reasoning mode:** Deduction - traced the exact code path, identified the guard condition that prevents the simplification, verified that applying the transformation manually produces the expected result.

**What needs to change:**
The condition at line 126 should also trigger when wrapping non-mod terms in `Mod(x, q)` produces a simplification. Specifically:
1. Save the original `non_mod_l` before transformation
2. Apply `non_mod_l = [cls(x, q) for x in non_mod_l]`
3. Check if this changed anything
4. Enter the distributive block if there was a change OR if mod_l had existing terms

## Edit sites
- `sympy/core/mod.py` lines 126-128: Change the guard condition from `if mod_l and all(...)` to check for changes in `non_mod_l` after wrapping, as shown in the suggested diff.

## Gate Loop - Iteration 1

**Drafted initial fix**: Moved wrapping logic before the condition check and added `changed` flag to detect simplification.

**Codex review**: Caught critical bug - the condition `changed or (mod_l and all(...))` would allow incompatible moduli when `changed = True`. Suggested: `if (not mod_l or all(inner.args[1] == q for inner in mod_l)) and (changed or mod_l)`.

**Applied corrected fix** with codex's suggested condition.

**Gate result**: FAIL - Different test failed: `assert (x - 3.3) % 1 == Mod(1.*x + 1 - point3, 1)`. 

**Trajectory**: Divergent (new failure, different from target test).

## Gate Loop - Iteration 2

**Root cause of regression**: Fix caused `Mod(1.0*x, 1)` to simplify to `0` when `x` has no integer assumption, breaking float handling test.

**Analysis**: The distributive property `Mod(a*b, q) = Mod(Mod(a,q)*Mod(b,q), q)` only holds for integers. Wrapping `1.0` and `x` gives `[0, Mod(x, 1)]`, then the block returns `0 * Mod(x, 1) = 0`, which is wrong when `x.is_integer = None`.

**Fix**: Added `p.is_integer` check to condition: `if p.is_integer and (not mod_l or all(...)) and (changed or mod_l)`.

**Gate result**: FAIL - Different test failed: `assert Mod(Mod(x + 2, 4)*(x + 4), 4) == Mod(x*(x + 2), 4)`.

**Trajectory**: Oscillatory (broke different test).

## Gate Loop - Iteration 3

**Root cause**: The `p.is_integer` check blocked the original behavior where existing Mod terms allow simplification even without integer guarantees.

**Analysis**: Two distinct cases:
1. Original behavior: If there are existing `Mod` terms with matching moduli, simplify (no integer check needed)
2. New behavior: If wrapping produces simplification AND all terms are integers, simplify (needs integer check)

**Final fix**: Changed condition to OR the two cases:
```python
if (mod_l and all(inner.args[1] == q for inner in mod_l)) or (p.is_integer and changed):
```

This preserves original behavior for case with existing Mod terms, and adds new behavior for integer-only wrapping simplification.

**Gate result**: PASS - All 82 tests passed, 3 expected failures.

**Trajectory**: Convergent (resolved).

## Resolution

**Status**: RESOLVED

**Final changes**:
- Lines 126-128 in `sympy/core/mod.py`: Added wrapping logic before condition check
- Line 130: Updated condition to enable simplification when either (1) existing compatible Mod terms present, OR (2) wrapping simplified terms and all factors are integers
- Removed redundant wrapping from inside the block

**Test results**: `test_Mod` passes, including `assert Mod(3*i, 2) == Mod(i, 2)`.

## Audit Results

**Gate execution**: All 82 tests passed, 3 expected failures (pre-existing).

### FAIL_TO_PASS
- test_Mod: **PASS** ✓

### PASS_TO_PASS regressions
None.

### Pre-existing failures (not counted, confirmed against base capture)
- test_evenness_in_ternary_integer_product_with_odd (expected failure)
- test_oddness_in_ternary_integer_product_with_odd (expected failure)
- test_issue_3531 (expected failure)

All three failures marked with 'f' (expected to fail) in both base capture and current gate output.

**VERDICT**: RESOLVED
**RE-ENTER**: none

The patch successfully fixes `Mod(3*i, 2)` to simplify to `Mod(i, 2)` without introducing any regressions.
