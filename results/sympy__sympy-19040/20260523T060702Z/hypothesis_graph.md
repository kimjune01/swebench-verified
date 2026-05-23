# Hypothesis graph: sympy__sympy-19040

## Hypothesis H1: dmp_ext_factor doesn't handle multivariate content correctly

**Classification**: Abduction (pattern match + code trace)
**Confidence**: 85%

**Symptom**: `factor((x - I*y)*(z - I*t), extension=[I])` returns only `x - I*y`, dropping the factor `z - I*t`.

**Root cause**: The `dmp_ext_factor` function in `sympy/polys/factortools.py` (lines 1138-1165) directly calls `dmp_sqf_part` on the input polynomial without first separating multivariate content from the primitive part. When `dmp_sqf_part` is applied to a multivariate polynomial like `(x-1)(y-1)`, it incorrectly computes the GCD with the derivative with respect to only the first variable, treating factors that don't involve the first variable as "repeated factors" and dividing them out.

For example, for `f = (x-1)(y-1)`:
- `df/dx = y-1`
- `gcd(f, df/dx) = y-1` (incorrectly treating `y-1` as a repeated factor)
- `sqf_part = f / gcd = x-1` (missing the `y-1` factor)

The correct approach (used by `dmp_zz_factor`) is to first separate the polynomial into content and primitive part using `dmp_primitive`, then factor each separately.

**Evidence**:
- `sympy/polys/factortools.py:1138-1165` - `dmp_ext_factor` implementation
- `sympy/polys/factortools.py:1042-1100` - `dmp_zz_factor` uses content/primitive separation
- Manual trace shows `dmp_sqf_part((x-1)(y-1))` returns `x-1` instead of `(x-1)(y-1)`

**Edit site**: `sympy/polys/factortools.py` lines 1138-1165 (`dmp_ext_factor` function)

**Rejected alternative**: Fixing `dmp_sqf_part` itself would require a more invasive change to the square-free factorization algorithm and would affect many other callers. The targeted fix in `dmp_ext_factor` follows the established pattern from `dmp_zz_factor`.


## Craft Gate Loop

### Gate Run 1 - Import Error
**Status:** NameError - `dmp_one_p` not defined
**Trajectory:** Divergent (syntax/import error)
**Action:** Added `dmp_one_p` to imports from `sympy.polys.densebasic`

### Gate Run 2 - Timeout
**Status:** Timeout after 120s
**Trajectory:** Hang in execution
**Diagnosis:** Added debug output, discovered hang in `dmp_sqf_norm` at u=2 during recursive factoring of content. The issue was calling `dmp_sqf_norm` on a primitive part with degree 0 in the main variable.

### Gate Run 3 - Indentation Error
**Status:** IndentationError from empty else block
**Trajectory:** Syntax error
**Action:** Removed empty else block created when cleaning up debug output

### Gate Run 4 - GREEN
**Status:** All 150 tests passed, including `test_issue_5786` ✓
**Trajectory:** Convergent (success)

## Resolution

The fix successfully implements content/primitive separation in `dmp_ext_factor`, following the pattern from `dmp_zz_factor`:

1. **Separate content and primitive part** using `dmp_primitive`
2. **Factor primitive part only if `dmp_degree(prim, u) > 0`** - This check prevents hanging on primitives with degree 0 in the main variable
3. **Recursively factor the content** at level u-1
4. **Combine factors** via trial division on the original polynomial with primitive factors, then prepend content factors wrapped as `[g]` to raise them from u-1 to u variables

**Key insight:** The check `if dmp_degree(prim, u) > 0` was critical - without it, `dmp_sqf_norm` would hang on polynomials with degree 0 in the main variable.

The recon diagnosis was correct: the bug was indeed the missing content/primitive separation before `dmp_sqf_part`.

**RESOLVED**
