# Hypothesis graph: django__django-13212

## Hypothesis H₁ (recon initial diagnosis)
**Status**: Active  
**Type**: Abduction → Deduction  
**Confidence**: 95%

**Observation**: Tests expect `%(value)s` placeholder in custom error messages to be replaced with the actual invalid value, but it shows literally as `%(value)s`.

**Root cause**: Validators raise `ValidationError` without passing the `value` parameter in the `params` dict. The `ValidationError.__iter__` method (django/core/exceptions.py:~165) performs string interpolation (`message %= error.params`) only when `error.params` is present.

**Evidence**:
- django/core/exceptions.py:165 - `if error.params: message %= error.params`
- django/core/validators.py:343 - BaseValidator already includes 'value' in params (tests pass for MaxLengthValidator, MinLengthValidator)
- django/core/validators.py:51 - RegexValidator raises without params
- django/core/validators.py:103,107,118,135,142 - URLValidator raises without params
- django/core/validators.py:211,216,228 - EmailValidator raises without params
- django/core/validators.py:275,280,290 - IP validators raise without params
- django/core/validators.py:441 - DecimalValidator 'invalid' error raises without params
- django/core/validators.py:553 - ProhibitNullCharactersValidator raises without params

**Edit sites** (all in django/core/validators.py):
- Line 51: RegexValidator - add `params={'value': value}`
- Lines 103, 107, 118, 135, 142: URLValidator - add `params={'value': value}`
- Lines 211, 216, 228: EmailValidator - add `params={'value': value}`
- Line 275: validate_ipv4_address - add `params={'value': value}`
- Line 280: validate_ipv6_address - add `params={'value': value}`
- Line 290: validate_ipv46_address - add `params={'value': value}`
- Line 441: DecimalValidator 'invalid' - add `params={'value': value}`
- Lines 460, 466, 473: DecimalValidator other errors - add `'value': value` to existing params
- Line ~507: FileExtensionValidator - add `'value': value.name` to existing params
- Line 553: ProhibitNullCharactersValidator - add `params={'value': value}`


## Gate Loop - Craft Phase

### Iteration 1: Initial Fix Applied
Applied the recon diagnosis: added `params={'value': value}` to all ValidationError raises in validators:
- RegexValidator (1 site)
- URLValidator (5 sites)
- EmailValidator (3 sites)
- validate_ipv4_address, validate_ipv6_address, validate_ipv46_address (3 sites)
- DecimalValidator (4 sites - added value to existing params)
- FileExtensionValidator (1 site - added value.name to existing params)
- ProhibitNullCharactersValidator (1 site)

**Gate Result**: 6/7 tests passed. 1 failure in test_value_placeholder_with_decimal_field (value='NaN').

**Error**: `AssertionError: {'field': ['%(value)s']} != {'field': ['NaN']}`
The placeholder was not being interpolated - the error message was literally '%(value)s'.

**Analysis**: The other DecimalValidator cases (max_digits, max_decimal_places, max_whole_digits) passed, but the 'invalid' case failed. This suggested the error was being raised from a different location.

### Iteration 2: Root Cause Found
Traced through DecimalField implementation and found that `DecimalField.validate()` method (not the DecimalValidator) raises ValidationError for non-finite values like NaN:
```python
if not value.is_finite():
    raise ValidationError(self.error_messages['invalid'], code='invalid')
```

This happens BEFORE DecimalValidator runs, and was not passing params.

**Fix**: Added `params={'value': value}` to DecimalField.validate() in django/forms/fields.py line 358.

**Gate Result**: ✅ All 7 tests pass!

**Status**: RESOLVED

## Audit Phase - Final Verification

**Date**: 2026-05-22  
**Patch Status**: Live (2 files modified: django/core/validators.py, django/forms/fields.py)

### FAIL_TO_PASS Results
All 5 tests now PASS:
- ✅ test_value_placeholder_with_char_field - PASS
- ✅ test_value_placeholder_with_decimal_field - PASS
- ✅ test_value_placeholder_with_file_field - PASS
- ✅ test_value_placeholder_with_integer_field - PASS
- ✅ test_value_placeholder_with_null_character - PASS

### PASS_TO_PASS Results
All 2 tests still PASS:
- ✅ test_all_errors_get_reported - PASS
- ✅ test_field_validators_can_be_any_iterable - PASS

### Regressions
None detected. All 7 tests passed cleanly.

### Pre-existing Failures
The fail-on-base capture showed 6 test failures before the patch (all test_value_placeholder_with_char_field variants). All now resolved.

### Summary
The patch successfully:
1. Fixed all validators to include `params={'value': value}` when raising ValidationError
2. Fixed DecimalField.validate() to pass params for non-finite values
3. Maintained backward compatibility - no regressions
4. Achieved 100% coverage of FAIL_TO_PASS tests

**Final Status**: ✅ RESOLVED
