# Hypothesis graph: django__django-16899
# Hypothesis Graph: django__django-16899

## H₀: The tests fail because the readonly_fields error message doesn't include the field name
**Status**: Active
**Type**: Abduction
**Confidence**: 95% (deduction from code reading)

### Evidence
1. Test `test_nonexistent_field` expects:
   ```
   "The value of 'readonly_fields[1]' refers to 'nonexistent', which is not a callable, an attribute of 'SongAdmin', or an attribute of 'admin_checks.Song'."
   ```

2. Test `test_nonexistent_field_on_inline` expects:
   ```
   "The value of 'readonly_fields[0]' refers to 'i_dont_exist', which is not a callable, an attribute of 'CityInline', or an attribute of 'admin_checks.City'."
   ```

3. Actual error message at `django/contrib/admin/checks.py:773-776`:
   ```python
   "The value of '%s' is not a callable, an attribute of '%s', or an attribute of '%s'." % (label, obj.__class__.__name__, obj.model._meta.label,)
   ```
   Missing: `refers to '%s', which` with the `field_name` parameter

4. Other admin checks (e.g., line 570, 906, 962, 1105, 1139) follow the pattern:
   ```python
   "The value of '%s' refers to '%s', which ..." % (label, field_name, ...)
   ```

### Root Cause
The `_check_readonly_fields_item` method at `django/contrib/admin/checks.py:761-785` generates error E035 without including the field name in the message, unlike other similar admin check errors.

### Edit Sites
- `django/contrib/admin/checks.py` lines 773-780: Change error message format from:
  ```python
  "The value of '%s' is not a callable, an attribute of '%s', or an attribute of '%s'." % (label, obj.__class__.__name__, obj.model._meta.label,)
  ```
  To:
  ```python
  "The value of '%s' refers to '%s', which is not a callable, an attribute of '%s', or an attribute of '%s'." % (label, field_name, obj.__class__.__name__, obj.model._meta.label,)
  ```

## Gate Loop Node 1

**Action**: Applied fix from recon handoff - modified `django/contrib/admin/checks.py` lines 773-780 to add field name to error message E035.

**Change**:
- Updated error message from: `"The value of '%s' is not a callable, an attribute of '%s', or an attribute of '%s'."`
- To: `"The value of '%s' refers to '%s', which is not a callable, an attribute of '%s', or an attribute of '%s'."`
- Added `field_name` parameter in the format tuple after `label`

**Codex pre-gate review**: Patch is correct. No structural issues identified.

**Gate result**: ✅ PASS - All 56 tests passed, including both FAIL_TO_PASS tests:
- test_nonexistent_field 
- test_nonexistent_field_on_inline

**Trajectory**: Convergent-success (green on first gate attempt)

---

# Audit: django__django-16899

## FAIL_TO_PASS
- test_nonexistent_field (admin_checks.tests.SystemChecksTestCase.test_nonexistent_field): **PASS** ✓
- test_nonexistent_field_on_inline (admin_checks.tests.SystemChecksTestCase.test_nonexistent_field_on_inline): **PASS** ✓

## PASS_TO_PASS regressions
None — all 54 PASS_TO_PASS tests remain passing.

## Pre-existing failures
None — the fail-on-base capture showed all tests passing before the patch.

## Analysis
The patch modifies `django/contrib/admin/checks.py` lines 773-780 to add the field name to error message E035, changing the format from:
```
"The value of '%s' is not a callable, an attribute of '%s', or an attribute of '%s'."
```
to:
```
"The value of '%s' refers to '%s', which is not a callable, an attribute of '%s', or an attribute of '%s'."
```

This minimal change:
1. Solves both FAIL_TO_PASS tests by including the missing field name in the error message
2. Introduces zero regressions — all 54 PASS_TO_PASS tests still pass
3. Aligns E035 error format with other admin check errors in the same file

Gate output: 56 tests ran, 56 passed (0.018s).

VERDICT: RESOLVED
RE-ENTER: none
