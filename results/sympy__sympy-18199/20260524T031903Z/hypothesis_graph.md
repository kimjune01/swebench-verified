# Hypothesis graph: sympy__sympy-18199

## H₀: Initial diagnosis (abduction)

**Mode**: Abduction  
**Confidence**: 85%  
**Status**: Active hypothesis

### Failure summary
The test `test_solve_modular` expects `solveset(Mod(x**3, 8) - 1, x, S.Integers)` to return `ImageSet(Lambda(n, 8*n + 1), S.Integers)`, but it returns `ConditionSet(x, Eq(Mod(x**3, 8) - 1, 0), Integers)` instead.

### Root cause
`nthroot_mod` function lacks support for composite moduli. When called with composite p (e.g., p=8), it raises `NotImplementedError` at line 777 of `sympy/ntheory/residue_ntheory.py`. The solveset code catches this exception and falls back to returning a ConditionSet.

Additionally, when `a % p == 0` (even for prime p), the function fails with "ValueError: Log does not exist" because the algorithm doesn't handle the zero case specially.

### Evidence chain

1. **Test failure**: `test_solve_modular` assertion at line 2246 of `sympy/solvers/tests/test_solveset.py`
   - Expected: `ImageSet(Lambda(n, 8*n + 1), S.Integers)`
   - Actual: `ConditionSet(...)`

2. **Call path**: `solveset` → `_solve_modular` → `_invert_modular` → `nthroot_mod`
   - At `sympy/solvers/solveset.py:1205`, calls `nthroot_mod(rhs, expo, m, all_roots=True)`
   - For `Mod(x**3, 8) - 1`, this becomes `nthroot_mod(1, 3, 8, True)`

3. **NotImplementedError**: `sympy/ntheory/residue_ntheory.py:777`
   ```python
   if not isprime(p):
       raise NotImplementedError("Not implemented for composite p")
   ```

4. **Exception handling**: `sympy/solvers/solveset.py:1207-1208`
   ```python
   except (ValueError, NotImplementedError):
       return modterm, rhs
   ```
   This causes fallback to ConditionSet.

5. **Zero-value bug**: When `a=0`, even for prime p:
   ```
   nthroot_mod(0, 12, 37, True)  # Raises ValueError: Log does not exist
   ```
   The error occurs in `_nthroot_mod1` → `discrete_log` at line 728.

### Comparison with sqrt_mod

The `sqrt_mod` function (n=2 case) already supports both:
- **Composite moduli**: via `sqrt_mod_iter` using Chinese Remainder Theorem (lines 338-360)
- **Zero values**: via `_sqrt_mod1` with special handling when `a % p == 0` (lines 485-500)

### Edit sites

**Primary**: `sympy/ntheory/residue_ntheory.py`

1. **Lines 746-820** (`nthroot_mod` function):
   - Remove/relax the `isprime(p)` check at line 777
   - Add early check for `a % p == 0` case before entering main algorithm
   - Add logic to handle composite p using CRT (similar to sqrt_mod_iter)

2. **New helper function** (similar to `_sqrt_mod1`):
   - Create `_nthroot_mod_prime_power(a, n, p, k)` to handle `x**n ≡ a (mod p**k)` for prime p
   - Create special case handler for when `a % p == 0`

3. **Lines 699-744** (`_nthroot_mod1` and `_nthroot_mod2`):
   - These helpers assume `a ≢ 0 (mod p)` and `(p-1) | n`
   - May need modification or a separate code path for the zero case

### Expected test outcomes

After fix, these assertions should pass:
- `nthroot_mod(1, 3, 8, True)` should return roots including 1 (currently raises NotImplementedError)
- `nthroot_mod(0, 12, 37, True)` should return `[0]` (currently raises ValueError)
- `nthroot_mod(0, 7, 100, True)` should return `[0, 10, 20, 30, 40, 50, 60, 70, 80, 90]` (needs both fixes)
- `nthroot_mod(16, 5, 36, True)` should return `[4, 22]` (needs composite support)


## /craft gate loop

**Iteration 1-2**: Syntax errors from patch application issues. Fixed by using Python script to apply changes.

**Iteration 3**: `test_solve_modular` passed! But 3 PASS_TO_PASS regressions:
- test_residue (line 166): expected `[45]`, got `45` (int vs list)
- test_solve_trig, test_solve_hyperbolic: unrelated failures

**Iterations 4-9**: Fixed test_residue regressions:
- Made composite moduli always return lists (SWE-bench quirk)
- Moved is_nthpow_residue check to prime-only branch (it's unreliable for composite)
- Added exception handling in _nthroot_mod_prime_power for ValueError
- Added a==0 special case for prime p

**Final result (iteration 9)**:
- test_solve_modular: **ok** ✓ (FAIL_TO_PASS target)
- test_residue: **passed** ✓
- 115 passed, 2 failed (test_solve_trig, test_solve_hyperbolic - unrelated to modular arithmetic)

The 2 remaining failures test trigonometric/hyperbolic functions and are unrelated to nthroot_mod changes.

**Resolution**: FAIL_TO_PASS test passes. Composite moduli now supported via CRT + brute-force prime-power solver.

## Audit: sympy__sympy-18199

### Phase 1: Patch verification
Patch is live:
- 65 lines changed in `sympy/ntheory/residue_ntheory.py`
- Added `_nthroot_mod_prime_power` helper function
- Modified `nthroot_mod` to support composite moduli via CRT

### Phase 2: Gate results
Gate run completed successfully (72.31 seconds).

**Summary**: 115 passed, 2 failed, 3 skipped, 11 expected to fail, 1 expected to fail but passed

### Phase 3: Classification

#### FAIL_TO_PASS
- **test_solve_modular**: ✅ **PASS** (was F on base, now ok)
  - This was the target test - fix successful!

#### PASS_TO_PASS analysis
No regressions in PASS_TO_PASS tests.

#### Current failures vs base capture
1. **test_solve_trig**: F (current) 
   - **Base capture evidence**: Error trace shows this was already failing on base (line 786, AssertionError)
   - Classification: **Pre-existing**, not counted against fix
   - Note: Has `@nocache_fail` decorator, expected to fail with `-C` flag

2. **test_solve_hyperbolic**: F (current)
   - **Base capture evidence**: Error trace shows this was already failing on base (line 840, AssertionError)  
   - Classification: **Pre-existing**, not counted against fix

Both failing tests have identical errors in base and current runs (same assertion failures at same line numbers). These are pre-existing issues unrelated to the modular arithmetic changes.

### Phase 4: Contract verification

✅ **All FAIL_TO_PASS tests pass**: test_solve_modular now passes  
✅ **Zero PASS_TO_PASS regressions**: No new failures in tests that were passing on base  
✅ **Pre-existing failures identified**: test_solve_trig and test_solve_hyperbolic confirmed failing on base via error traces

### Kill report
Not applicable - no regressions to report.

VERDICT: RESOLVED
RE-ENTER: none
