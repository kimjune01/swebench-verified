# Hypothesis graph: django__django-16485

## H₀: Precision calculation can result in invalid value (abduction → deduction)

**Observation:** `floatformat("0.00", 0)` crashes with `ValueError: valid range for prec is [1, MAX_PREC]` at line 190 in defaultfilters.py.

**Trace:**
1. Input: `text="0.00"`, `arg=0` → converted to `d=Decimal("0.00")`, `p=0`
2. Calculate fractional part: `m = int(d) - d = 0 - 0.00 = Decimal("0.00")` (falsy)
3. Line 182-186: Calculate precision for Context:
   - `tupl = d.as_tuple()` → `DecimalTuple(sign=0, digits=(0,), exponent=-2)`
   - `units = len(tupl[1]) = 1`
   - `units += -tupl[2] if m else tupl[2]` → since m is falsy, `units += -2` → `units = -1`
   - `prec = abs(p) + units + 1 = 0 + (-1) + 1 = 0`
4. Line 190: `Context(prec=0)` fails - Context requires prec >= 1

**Root cause:** The precision formula at line 186 can produce prec=0 (or negative) when:
- Number has no fractional part (m is falsy)
- Number has negative exponent (e.g., "0.00" has exponent -2)
- p=0 (no decimal places requested)

This is a regression from commit 12f7928f5a (issue #27394) which changed:
```python
units = len(tupl[1]) - tupl[2]  # old
```
to:
```python
units = len(tupl[1])
units += -tupl[2] if m else tupl[2]  # new
```

The new formula fixed large integers (positive exponents) but didn't account for zero-valued decimals with negative exponents.

**Fix:** Line 186: ensure `prec >= 1`
```python
prec = max(1, abs(p) + units + 1)
```

**Evidence:**
- django/template/defaultfilters.py:186 - prec calculation
- django/template/defaultfilters.py:190 - Context(prec=prec) call that crashes
- Verified fix doesn't regress tests for #15789 or #27394

**Status:** ROOT CAUSE IDENTIFIED (deduction - 99%)

## Craft: Gate Loop

### Iteration 1: Initial fix applied

**Diff applied:**
```diff
--- a/django/template/defaultfilters.py
+++ b/django/template/defaultfilters.py
@@ -183,7 +183,7 @@ def floatformat(text, arg=-1):
     tupl = d.as_tuple()
     units = len(tupl[1])
     units += -tupl[2] if m else tupl[2]
-    prec = abs(p) + units + 1
+    prec = max(1, abs(p) + units + 1)
 
     # Avoid conversion to scientific notation by accessing `sign`, `digits`,
     # and `exponent` from Decimal.as_tuple() directly.
```

**Codex review:** No blocker. The `max(1, ...)` guard correctly prevents `Context(prec=0)` crashes while preserving correct behavior for all edge cases. Zero-valued Decimals with negative exponents can produce `prec <= 0` in the original formula, and `prec=1` is sufficient for quantizing zeros.

**Gate result:** ✅ PASS

All 10 tests passed:
- test_zero_values (FAIL_TO_PASS) ✅
- test_floatformat01 ✅
- test_floatformat02 ✅
- test_float_dunder_method ✅
- test_force_grouping ✅
- test_infinity ✅
- test_inputs ✅
- test_low_decimal_precision (regression test for #15789) ✅
- test_negative_zero_values ✅
- test_unlocalize ✅

**Trajectory:** Convergent-resolved (first iteration success)

**Resolution:** RESOLVED

## Audit: django__django-16485

### Patch confirmed live
```
 django/template/defaultfilters.py | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

Change: `prec = max(1, abs(p) + units + 1)` ensures prec >= 1

### FAIL_TO_PASS
- test_zero_values: **PASS** ✓

### PASS_TO_PASS
- test_floatformat01: **PASS** ✓
- test_floatformat02: **PASS** ✓
- test_float_dunder_method: **PASS** ✓
- test_force_grouping: **PASS** ✓
- test_infinity: **PASS** ✓
- test_inputs: **PASS** ✓
- test_low_decimal_precision (#15789): **PASS** ✓
- test_negative_zero_values: **PASS** ✓
- test_unlocalize: **PASS** ✓

### PASS_TO_PASS regressions
**None**

### Pre-existing failures (not counted)
**None**

### Contract status
✅ All FAIL_TO_PASS tests pass (1/1)
✅ Zero PASS_TO_PASS regressions (0/9)

VERDICT: RESOLVED
RE-ENTER: none
