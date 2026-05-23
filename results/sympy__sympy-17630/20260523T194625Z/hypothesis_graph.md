# Hypothesis graph: sympy__sympy-17630
## H₀ (Abduction - 85%)
Tests fail because `Add(ZeroMatrix, ZeroMatrix)` returns scalar `Zero` instead of `ZeroMatrix`, breaking BlockMatrix multiplication and ZeroMatrix addition.

### Symptom
1. `test_zero_matrix_add`: `Add(ZeroMatrix(2,2), ZeroMatrix(2,2))` returns scalar `Zero` instead of `ZeroMatrix(2,2)`
2. `test_issue_17624`: After `BlockMatrix._blockmul`, the result blocks contain scalar `Zero` instead of `ZeroMatrix`, causing `ValueError: expecting a sequence of 1 or more rows containing Matrices`

### Root cause traced
When `Add(ZeroMatrix, ZeroMatrix)` is called:
1. Add's postprocessor in `sympy/matrices/expressions/matexpr.py:631` constructs `MatAdd(S.Zero, zm1, zm2)` because it incorrectly prepends `Add.identity` (scalar S.Zero) when nonmatrices is empty
2. MatAdd.doit() applies the rm_id rule which removes all zero-like args and keeps the FIRST one (rm_id keeps one identity when all args are identities)
3. Since S.Zero was prepended as the first arg, rm_id keeps S.Zero instead of ZeroMatrix
4. Result: scalar Zero instead of ZeroMatrix

This cascades to BlockMatrix:
- `BlockMatrix._blockmul` uses matrix multiplication on the underlying ImmutableDenseMatrix
- Matrix multiplication in `sympy/matrices/dense.py:198` uses `Add(*vec)` to sum products
- This calls core Add, not MatAdd, triggering the buggy postprocessor
- Result blocks contain scalar Zero, not ZeroMatrix
- BlockMatrix.__new__ validation rejects scalar Zero (not a Matrix), raising ValueError


## Edit site
- `sympy/matrices/expressions/matexpr.py:631` — Line unconditionally prepends `cls._from_args(nonmatrices)` which is `S.Zero` when nonmatrices is empty. Fix: check if nonmatrices is empty, if so call `mat_class(*matrices).doit(deep=False)` without prepending scalar identity.

## Evidence
- Tested: `MatAdd(zm1, zm2).doit()` → ZeroMatrix ✓
- Tested: `MatAdd(S.Zero, zm1, zm2).doit()` → scalar Zero ✗
- Tested: `Add(zm1, zm2)` → calls postprocessor → scalar Zero ✗
- Tested: `zm1 + zm2` → uses MatAdd directly → ZeroMatrix ✓

## Craft Gate Loop

### Iteration 1: Initial fix applied
**Hypothesis**: The Add postprocessor incorrectly prepends scalar S.Zero when nonmatrices is empty, causing MatAdd(S.Zero, ZeroMatrix, ZeroMatrix) instead of MatAdd(ZeroMatrix, ZeroMatrix).

**Fix**: Modified get_postprocessor to check `if cls == Add and not nonmatrices:` and return `mat_class(*matrices).doit(deep=False)` without prepending the scalar zero.

**Codex review**: Approved. Targeted to Add only, preserves existing Mul behavior.

**Gate result**: ✅ GREEN
- test_issue_17624: ok
- test_zero_matrix_add: ok
- All 22 tests passed, 1 expected fail

**Classification**: Convergent-resolved on first iteration.

# Audit: sympy__sympy-17630

## FAIL_TO_PASS
- test_issue_17624: PASS ✓
- test_zero_matrix_add: PASS ✓

## PASS_TO_PASS regressions
none

## Pre-existing (not counted, confirmed against base capture)
none

## Verdict
All FAIL_TO_PASS tests now pass. All PASS_TO_PASS tests remain passing. Zero regressions detected. Patch successfully resolves the issue.

VERDICT: RESOLVED
RE-ENTER: none
