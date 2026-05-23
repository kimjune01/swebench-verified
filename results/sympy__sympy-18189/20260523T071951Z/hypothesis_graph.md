# Hypothesis graph: sympy__sympy-18189

## H₀ (abduction): Recursive call drops permute parameter

**Observation**: Test `test_diophantine` fails at line 554 because `diophantine(y**4 + x**4 - 2**4 - 3**4, syms=(y, x), permute=True)` returns only `{(3, 2)}` instead of all 8 permutations.

**Hypothesis**: When `syms` parameter differs from alphabetically sorted variables, the function takes an early return (line 184-185) that recursively calls `diophantine(eq, param)` without passing the `permute` parameter, causing it to default to `False`.

**Evidence**:
- `sympy/solvers/diophantine.py:177-185` - syms reordering logic
- `sympy/solvers/diophantine.py:185` - recursive call: `diophantine(eq, param)` missing `permute=permute`
- Alphabetical sorting: variables are sorted as `[x, y]` (line 176)
- When `syms=(x, y)`: matches sorted order, continues with `permute=True` → 8 solutions
- When `syms=(y, x)`: doesn't match, takes early return with `permute=False` → 1 solution

**Root cause**: Line 185 should pass `permute=permute` to preserve the parameter in recursive call.

**Reasoning mode**: Deduction (traced code path, identified missing parameter)
**Confidence**: 95%


## Gate Loop Node 1 - RESOLVED

**Iteration:** 1/8
**Status:** ✅ GREEN

**Applied Fix:**
- Line 185: `diophantine(eq, param)` → `diophantine(eq, param, permute=permute)`
- Line 190: `diophantine(d)` → `diophantine(d, param, permute=permute)`
- Line 191: `diophantine(n)` → `diophantine(n, param, permute=permute)`

**Gate Result:**
```
== tests finished: 43 passed, 1 skipped, 2 expected to fail, in 20.61 seconds ==
```

**Trajectory:** Convergent (immediate resolution)

All FAIL_TO_PASS tests pass on first iteration. The recon diagnosis was accurate: the recursive `diophantine()` calls were missing the `permute` parameter, causing it to default to `False` when symbol reordering was needed. Adding `permute=permute` to all three recursive call sites fixed the issue.


## Audit: sympy__sympy-18189

### Phase 3: Classification

**FAIL_TO_PASS:**
- test_diophantine: **PASS** ✓

**PASS_TO_PASS regressions:** None

**Pre-existing failures (not counted):** None

### Gate Comparison

**Baseline (fail-on-base):**
- 42 passed, 1 failed (test_diophantine), 1 skipped, 2 expected to fail

**With patch applied:**
- 43 passed, 0 failed, 1 skipped, 2 expected to fail

### Result

The FAIL_TO_PASS test now passes and all PASS_TO_PASS tests remain passing. No regressions introduced.

**VERDICT: RESOLVED**
**RE-ENTER: none**
