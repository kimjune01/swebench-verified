# Hypothesis graph: sympy__sympy-15976

## H₀: Test failure baseline (abduction)
The test `test_presentation_symbol` fails at the assertion `assert mml.nodeName == 'msup'` when printing `Symbol("x^2")`. The test expects the root element to be `<msup>` but gets `<mi>` instead.

Actual output for `Symbol("x^2")`: `<mi><msup><mi>x</mi><mi>2</mi></msup></mi>`
Expected output: `<msup><mi>x</mi><mi>2</mi></msup>`

The superscript structure is being incorrectly wrapped inside a text identifier element.

## H₁: Root cause - msup/msub/msubsup incorrectly wrapped in <mi> (deduction - 99%)

**File**: `sympy/printing/mathml.py`
**Method**: `_print_Symbol` (lines 745-803)

**Evidence**:
1. Line 746: `x = self.dom.createElement('mi')` - creates an `<mi>` element
2. Lines 780-781: Creates `mname` as a separate `<mi>` element for the symbol name
3. Lines 786-801: When supers or subs exist, creates structural elements (`msub`/`msup`/`msubsup`) and **appends them to `x`**
4. Line 802: `return x` - returns the `<mi>` wrapper

**The bug**: The structural elements (msub/msup/msubsup) are appended to the `<mi>` element `x`, then `x` is returned. This creates malformed MathML like `<mi><msup>...</msup></mi>` where the structural element is incorrectly nested inside a text container.

**Supporting code quotes**:
- `sympy/printing/mathml.py:746` - `x = self.dom.createElement('mi')`
- `sympy/printing/mathml.py:786-789` - Creates `msub` and appends to `x`
- `sympy/printing/mathml.py:792-795` - Creates `msup` and appends to `x`
- `sympy/printing/mathml.py:797-801` - Creates `msubsup` and appends to `x`
- `sympy/printing/mathml.py:802` - `return x`

**Verified behavior**:
- `split_super_sub("x2")` returns `('x', [], ['2'])` - trailing digits treated as subscript
- `split_super_sub("x^2")` returns `('x', ['2'], [])` - caret notation treated as superscript
- Current output for `x^2`: `<mi><msub><mi>x</mi><mi>2</mi></msub></mi>` (malformed)
- Current output for `x2`: `<mi><msub><mi>x</mi><mi>2</mi></msub></mi>` (malformed)

**Why this causes invisible rendering**: The `<mi>` element is a text container in MathML and should only contain text nodes or simple markup. When it contains a structural element like `<msup>`, browsers may fail to render it correctly, treating the content as malformed and making it invisible.

**Confidence**: Deduction - 99%. Direct code trace from test failure to implementation, with verified malformed output.


## Craft Gate Loop (iteration 1)

**Hypothesis**: The root cause from recon is correct — `_print_Symbol` wraps structural elements in `<mi>` instead of returning them directly.

**Fix Applied**:
- Added bold attribute handling to `mname` (the base `<mi>` element) instead of wrapper `x`
- Changed all branches to return the appropriate element directly:
  - Plain symbols: return `mname`
  - Subscripts: return `msub`
  - Superscripts: return `msup`
  - Both: return `msubsup`

**codex Review (2 volleys)**:
- First volley: Caught missing bold attribute handling for structural elements
- Second volley: Caught that plain case also needs to use `mname` for bold consistency
- Approved final version with bold applied to `mname` consistently across all paths

**Gate Result**: ✅ PASS (39/39 tests passed)

**Trajectory**: Convergent-success — first gate run passed after codex pre-filtering

**Resolution**: FAIL_TO_PASS test `test_presentation_symbol` now passes. The fix correctly produces:
- `Symbol("x^2")` → `<msup><mi>x</mi><mi>2</mi></msup>` (not wrapped in `<mi>`)
- `Symbol("x_2")` → `<msub><mi>x</mi><mi>2</mi></msub>` (not wrapped in `<mi>`)
- Bold styling preserved on the base `<mi>` element for all cases

---

# Audit: sympy__sympy-15976

## FAIL_TO_PASS
- test_presentation_symbol: **PASS** ✅

## PASS_TO_PASS regressions
None — all 38 PASS_TO_PASS tests remain passing.

## Pre-existing failures
None applicable — the baseline showed only `test_presentation_symbol` failing, which is now fixed.

## Verdict Rationale
- ✅ All FAIL_TO_PASS tests pass (1/1)
- ✅ Zero PASS_TO_PASS regressions (0/38)
- ✅ Gate output: 39 passed, 0 failed

The fix successfully resolves the issue without introducing any regressions. The structural MathML elements (msup/msub/msubsup) are now returned directly instead of being wrapped in an `<mi>` container, producing correct MathML output.

VERDICT: RESOLVED
RE-ENTER: none
