# Hypothesis graph: django__django-13023

## H₀: TypeError not caught in DecimalField.to_python() (abduction)

**Observation**: The test `test_invalid_value` fails when calling `field.clean()` with invalid values like `{}`, `set()`, `object()`, `complex()`, and `b'bytes'`. The error shows:
- `TypeError: conversion from <type> to Decimal is not supported`
- Raised at `django/db/models/fields/__init__.py:1503` in `DecimalField.to_python()`

**Hypothesis**: The `to_python()` method at lines 1495-1507 only catches `decimal.InvalidOperation` but the `decimal.Decimal()` constructor can raise:
- `TypeError` for dict, set, complex, bytes, object
- `ValueError` for list, tuple  
- `decimal.InvalidOperation` for invalid strings

**Evidence**:
- Line 1503: `return decimal.Decimal(value)` 
- Lines 1504-1508: Only catches `decimal.InvalidOperation`
- Empirical test shows dict raises TypeError, list raises ValueError

**Confidence**: Deduction — 95%

**Edit sites**:
- `django/db/models/fields/__init__.py` lines 1504-1508: Change exception handler from `except decimal.InvalidOperation:` to `except (decimal.InvalidOperation, TypeError, ValueError):`


## Gate Loop - Iteration 1

**Drafted fix**: Changed `django/db/models/fields/__init__.py` line 1504 from `except decimal.InvalidOperation:` to `except (decimal.InvalidOperation, TypeError, ValueError):` to catch all exception types that `decimal.Decimal()` raises for invalid inputs.

**codex volley**: codex confirmed the fix is correct for `test_invalid_value` (verified that `decimal.Decimal()` raises `TypeError` for dict/set/complex/bytes/object, `ValueError` for empty sequences, and `InvalidOperation` for bad strings). Noted that `test_lookup_really_big_value` likely involves a different code path but the fix wouldn't break it.

**Gate result**: ✅ PASS - All 12 DecimalFieldTests passed including both FAIL_TO_PASS tests:
- test_invalid_value: ok
- test_lookup_really_big_value: ok

**Status**: RESOLVED - Single-line fix successfully addresses both failing tests without breaking any existing tests.

---

# Audit: django__django-13023

## FAIL_TO_PASS
- test_invalid_value (model_fields.test_decimalfield.DecimalFieldTests): **PASS** ✓
- test_lookup_really_big_value (model_fields.test_decimalfield.DecimalFieldTests): **PASS** ✓

## PASS_TO_PASS regressions
None — all 9 PASS_TO_PASS tests remain passing.

## Pre-existing (not counted, confirmed against base capture)
- test_fetch_from_db_without_float_rounding: skipped on both base and patched (SQLite rounding limitation)

## Summary
The patch successfully resolves the issue by catching `TypeError` and `ValueError` in addition to `decimal.InvalidOperation` in `DecimalField.to_python()`. Both FAIL_TO_PASS tests now pass, and no PASS_TO_PASS tests regressed. The fix is minimal (one line changed) and correctly handles all exception types that `decimal.Decimal()` can raise for invalid inputs.
