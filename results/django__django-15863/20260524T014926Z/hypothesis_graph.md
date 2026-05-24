# Hypothesis graph: django__django-15863

## Hypothesis H1 (Iteration 1)

**Mode**: Deduction  
**Confidence**: 95%

**Failure**: The test `test_inputs` fails because `floatformat(Decimal("123456.123456789012345678901"), 21)` returns `"123456.123456789000000000000"` instead of `"123456.123456789012345678901"`. Precision is lost after approximately 15 decimal digits.

**Root Cause**: In `django/template/defaultfilters.py` lines 153-161, when `text` is a `Decimal` object, the code calls `repr(text)` which returns a string like `"Decimal('123456...')"`. This cannot be parsed by `Decimal()`, causing an `InvalidOperation` exception. The code then falls back to `Decimal(str(float(text)))` on line 159, which converts the Decimal to a float first. Since floats have limited precision (~15-17 significant digits), the high-precision decimal data is lost.

**Evidence**:
- `repr(Decimal("123456.123456789012345678901"))` returns `"Decimal('123456.123456789012345678901')"` 
- `Decimal("Decimal('123456.123456789012345678901')")` raises `InvalidOperation`
- `float(Decimal("123456.123456789012345678901"))` returns `123456.123456789` (precision lost)
- `Decimal(str(float(Decimal("123456.123456789012345678901"))))` returns `Decimal('123456.123456789')` (precision lost)

**Edit Sites**:
- `django/template/defaultfilters.py` lines 153-161: Add a check before the try block to detect if `text` is already a `Decimal` instance. If it is, use it directly without any conversion. Otherwise, proceed with the existing `repr()` logic. This preserves the full precision of Decimal objects while maintaining backward compatibility with float and string inputs.

Specifically: Insert `if isinstance(text, Decimal): d = text` before line 153, and wrap the existing try-except block in an `else` clause.

## Craft gate-loop

### Iteration 1: Draft and volley

**Drafted fix**: Add isinstance check before the existing try-except to preserve Decimal precision.

**codex review** (GPT-5.5): Caught critical bug - `input_val` undefined for Decimal inputs, causing UnboundLocalError when `return input_val` executes on line 165. Suggested fix: assign `input_val = str(text)` in the Decimal branch.

**Revised fix**: 
```python
if isinstance(text, Decimal):
    input_val = str(text)
    d = text
else:
    try:
        input_val = repr(text)
        d = Decimal(input_val)
    except InvalidOperation:
        try:
            d = Decimal(str(float(text)))
        except (ValueError, InvalidOperation, TypeError):
            return ""
```

Applied to `django/template/defaultfilters.py` lines 153-160.

**Gate result**: GREEN - all 10 tests pass
- `test_inputs` (FAIL_TO_PASS): ✓ passes - `floatformat(Decimal("123456.123456789012345678901"), 21)` returns full precision
- All PASS_TO_PASS tests: ✓ no regressions

**Trajectory**: Convergent success - fix addresses root cause (Decimal→float precision loss) by bypassing conversion entirely when input is already a Decimal.

## Audit: django__django-15863

### FAIL_TO_PASS
- test_inputs (template_tests.filter_tests.test_floatformat.FunctionTests): **PASS** ✓

### PASS_TO_PASS regressions
None. All 9 PASS_TO_PASS tests remain passing.

### Pre-existing failures (not counted, confirmed against base capture)
None.

### Contract verification
- ✓ All FAIL_TO_PASS tests now pass (1/1)
- ✓ Zero PASS_TO_PASS regressions (0/9)
- ✓ Patch is present in tree (django/template/defaultfilters.py modified)

The fix successfully preserves Decimal precision by detecting Decimal instances and using them directly, bypassing the float conversion that was causing precision loss.

VERDICT: RESOLVED
RE-ENTER: none
