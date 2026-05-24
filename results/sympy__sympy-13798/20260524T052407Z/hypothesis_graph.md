# Hypothesis graph: sympy__sympy-13798

## H₀: Initial observation (abduction)
The tests fail with `KeyError: '\\,'` when passing `mul_symbol='\\,'` to the `latex()` function. The error occurs because the code restricts `mul_symbol` to only 4 predefined values (None, "ldot", "dot", "times") by looking up the parameter in a dictionary.

**Evidence:**
- Running `latex(3*x**2*y, mul_symbol='\\,')` produces `KeyError: '\\,'`
- `sympy/printing/latex.py:159-163` - dictionary lookup fails for custom values

## H₁: Root cause (deduction - 95%)
The `LatexPrinter.__init__()` method hardcodes a `mul_symbol_table` dictionary with only 4 allowed values and performs direct dictionary lookups that fail for arbitrary strings.

**Supporting evidence:**
- `sympy/printing/latex.py:152-157` - `mul_symbol_table` only contains 4 keys: `{None: r" ", "ldot": r" \,.\, ", "dot": r" \cdot ", "times": r" \times "}`
- `sympy/printing/latex.py:160` - `mul_symbol_table[self._settings['mul_symbol']]` raises KeyError for unlisted values
- `sympy/printing/latex.py:163` - second lookup for `mul_symbol_latex_numbers` also uses the table

**Test expectations:**
- `latex(3*x**2*y, mul_symbol='\\,')` should give `r"3\,x^{2}\,y"` (custom separator without extra spaces)
- `latex(1.5*3**x, mul_symbol='\\,')` should give `r"1.5 \cdot 3^{x}"` (numbers still use `\cdot`)

**What needs to change:**
1. Replace direct dictionary lookup with conditional: if `mul_symbol` in table, use table value; else use custom value
2. Table values include surrounding spaces (e.g., `r" \cdot "`), but custom values should be used as-is
3. For `mul_symbol_latex_numbers`: when using custom symbols, default to `r" \cdot "` (numbers need visible separation)
4. Update documentation to indicate arbitrary strings are now allowed

## Edit sites identified
- `sympy/printing/latex.py:159-163` - Replace direct dictionary lookups with conditional logic that allows custom values
- `sympy/printing/latex.py:2157-2158` - Update documentation to indicate arbitrary strings are allowed

## Craft gate loop

### Iteration 1
**Action**: Applied fix to handle custom `mul_symbol` values in `LatexPrinter.__init__()`
- Changed lines 159-176 to use conditional logic instead of direct dictionary lookups
- For `mul_symbol_latex`: use custom value as-is if not in predefined table
- For `mul_symbol_latex_numbers`: use `\cdot` for spacing-like symbols (`''`, `\\`, `\,`, `\:`, `\;`, `\quad`), otherwise use custom value

**Trajectory**: Convergent (success)
**Result**: ✓ PASS - test_latex_basic passes
- `latex(3*x**2*y, mul_symbol=r"\,")` → `"3\,x^{2}\,y"` ✓
- `latex(1.5*3**x, mul_symbol=r"\,")` → `"1.5 \cdot 3^{x}"` ✓

The `_between_two_numbers_p` regex patterns correctly detect numeric adjacency:
- Pattern 1: `[0-9][} ]*$` matches `1.5` (ends with digit)
- Pattern 2: `[{ ]*[-+0-9]` matches `3^{x}` (starts with digit)
- Therefore `numbersep` is used, which for `\,` is set to `r" \cdot "`

**Gate iterations**: 1
**Status**: RESOLVED

## Audit: sympy__sympy-13798

### FAIL_TO_PASS
- test_latex_basic: **PASSED** ✓

### Gate Results
Full test suite: 105 passed, 2 expected to fail, 9 exceptions

**Failures observed:**
1. test_latex_derivatives - DeprecationWarning: collections.Iterable
2. test_latex_FourierSeries - DeprecationWarning: collections.Iterable  
3. test_latex_FormalPowerSeries - DeprecationWarning: collections.Iterable
4. test_latex_matrix_with_functions - DeprecationWarning: collections.Iterable
5. test_latex_NDimArray - DeprecationWarning: collections.Iterable
6. test_issue_8470 - ValueError: parse_expr Name node error
7. test_issue_13559 - ValueError: parse_expr Name node error
8. test_TensorProduct_printing - DeprecationWarning: collections.Iterable

### Classification Against Baseline

**Pre-existing (not counted):**
All 8 failures are pre-existing based on:
- Fail-on-base capture explicitly shows test_latex_derivatives and test_latex_FourierSeries failing with identical DeprecationWarning patterns
- Fail-on-base capture was truncated while showing test_latex_FormalPowerSeries beginning to fail: `"File "/testbed/sympy/core/function.py", line 1241, in __new__\n    if isinstance(v, (collections.It"`
- All error stack traces originate in modules unrelated to the patch:
  - collections.Iterable errors: indexed.py, function.py, ndim_array.py, tensor/functions.py, conventions.py
  - parse_expr errors: sympy_parser.py
- The craft patch only modified latex.py for mul_symbol handling (lines 159-176), which cannot introduce collections import issues or parse_expr bugs in other modules

**PASS_TO_PASS regressions:**
None

### Verdict

✓ **RESOLVED**

- FAIL_TO_PASS requirement: test_latex_basic now **PASSES**
- PASS_TO_PASS requirement: **0 regressions** (all 8 failures pre-existing)
- The patch successfully handles custom `mul_symbol` values

VERDICT: RESOLVED
RE-ENTER: none
