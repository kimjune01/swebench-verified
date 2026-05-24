# Hypothesis graph: django__django-11880

## H₀ (Abduction) - Initial observation
**Status:** Confirmed → Refined to H₁  
**Claim:** The test `test_field_deep_copy_error_messages` fails because deepcopy of a Field shares the same error_messages dictionary with the original.  
**Evidence:**
- Test failure: `AssertionError: unexpectedly identical: {'required': 'This field is required.', 'invalid': 'Form custom error message.'}`
- Test uses `assertIsNot(field_copy.error_messages, field.error_messages)` which checks object identity
- The error shows the dictionaries are the same object, not copies

## H₁ (Deduction) - Root cause localized
**Status:** Active  
**Claim:** `Field.__deepcopy__` at django/forms/fields.py:198-203 does not deepcopy the `error_messages` dictionary, causing all copies to share the same dictionary object.  
**Confidence:** 99% (deduction - traced through code)  
**Evidence:**
- `django/forms/fields.py:198-203` - Field.__deepcopy__ implementation:
  ```python
  def __deepcopy__(self, memo):
      result = copy.copy(self)  # Line 199: Shallow copy
      memo[id(self)] = result
      result.widget = copy.deepcopy(self.widget, memo)  # Widget is deepcopied
      result.validators = self.validators[:]  # Validators list is shallow copied
      return result
  ```
- Line 199 performs `copy.copy(self)` which creates a shallow copy - all attributes including `error_messages` are copied by reference
- Line 201 explicitly deepcopies `widget`
- Line 202 explicitly shallow-copies the `validators` list
- **No line deepcopies `error_messages`** - it remains a reference to the original dictionary
- `django/forms/fields.py:110-113` shows error_messages is a dictionary:
  ```python
  messages = {}
  for c in reversed(self.__class__.__mro__):
      messages.update(getattr(c, 'default_error_messages', {}))
  messages.update(error_messages or {})
  self.error_messages = messages
  ```
- `django/forms/forms.py:87` shows Form instances deepcopy fields: `self.fields = copy.deepcopy(self.base_fields)`
- This means all Form instances share the same error_messages dictionaries for their fields

**Why this matters:**
- The problem description states: "This is relevant for Forms and ModelForms that modify the error messages of their fields dynamically"
- When error_messages is modified on a copied field, the modification affects all copies
- Each Form instance is expected to have isolated fields, but they share error_messages

## Edit Sites

### Primary fix:
- `django/forms/fields.py:198-203` - Field.__deepcopy__ method
  - Add deepcopy of error_messages after line 202, before the return
  - Similar to how widget is deepcopied on line 201

### No other edit sites required:
- FileField.__deepcopy__ (line 767-769) calls `super().__deepcopy__(memo)`, so it will inherit the fix
- MultiValueField.__deepcopy__ (line 985-987) calls `super().__deepcopy__(memo)`, so it will inherit the fix
- No other Field subclasses override __deepcopy__ (verified by grep)

## Gate Loop - Iteration 1

**Hypothesis**: Add shallow copy of error_messages in Field.__deepcopy__ method

**Implementation**: Added `result.error_messages = self.error_messages.copy()` at line 203 in django/forms/fields.py, after the validators shallow copy and before the return statement.

**codex volley feedback**: Recommended using shallow dict copy (`self.error_messages.copy()`) instead of deepcopy to match the existing `validators` shallow-copy style and avoid potential issues with non-deepcopyable custom objects in error_messages.

**Gate result**: ✅ PASS - All 115 tests passed, including `test_field_deep_copy_error_messages`

**Trajectory**: Convergent success - FAIL_TO_PASS test now passes with minimal change

**Resolution**: RESOLVED - The fix creates a new error_messages dictionary instance for each deepcopied field, preventing shared mutable state between the original and copied fields.

---

# Audit: django__django-11880

## FAIL_TO_PASS
- test_field_deep_copy_error_messages (forms_tests.tests.test_forms.FormsTestCase): PASS ✓

## PASS_TO_PASS regressions
none

## Pre-existing (not counted, confirmed against base capture)
none

## Kill report
Not applicable - all tests pass.

**Patch content:**
```diff
diff --git a/django/forms/fields.py b/django/forms/fields.py
index 03cd8af8d7..171a36187e 100644
--- a/django/forms/fields.py
+++ b/django/forms/fields.py
@@ -200,6 +200,7 @@ class Field:
         memo[id(self)] = result
         result.widget = copy.deepcopy(self.widget, memo)
         result.validators = self.validators[:]
+        result.error_messages = self.error_messages.copy()
         return result
```

**Test suite results:** 115 tests run, all passed in 0.164s

VERDICT: RESOLVED
RE-ENTER: none
