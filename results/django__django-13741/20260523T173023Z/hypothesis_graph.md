# Hypothesis graph: django__django-13741

## H₀: ReadOnlyPasswordHashField missing disabled=True default (abduction)

**Observation**: Test `test_readonly_field_has_changed` fails with `AssertionError: False is not True` when asserting `field.disabled is True`.

**Trace**:
- Test instantiates `ReadOnlyPasswordHashField()` at `tests/auth_tests/test_forms.py:1024`
- Class defined at `django/contrib/auth/forms.py:54-67`
- `__init__` (lines 57-59) only sets `kwargs.setdefault("required", False)`, does not set `disabled`
- Base class `forms.Field.__init__` (django/forms/fields.py:59) defaults `disabled=False`
- Therefore `field.disabled` is `False`, not `True`

**Root cause**: `ReadOnlyPasswordHashField.__init__` does not default the `disabled` kwarg to `True`.

**Supporting evidence**:
- `django/contrib/auth/forms.py:57-59` — `__init__` only sets `required=False`, not `disabled=True`
- `django/forms/fields.py:59` — base Field defaults `disabled=False`
- Problem description states disabled fields ignore tampered values in favor of initial data, making them ideal for read-only password hashes

**Edit site**: `django/contrib/auth/forms.py:58` — add `kwargs.setdefault("disabled", True)` after the existing `required` line

**Confidence**: Deduction — 98%

## Gate iteration 1: PASS

**Diff applied**:
```diff
--- a/django/contrib/auth/forms.py
+++ b/django/contrib/auth/forms.py
@@ -56,6 +56,7 @@ class ReadOnlyPasswordHashField(forms.Field):
 
     def __init__(self, *args, **kwargs):
         kwargs.setdefault("required", False)
+        kwargs.setdefault("disabled", True)
         super().__init__(*args, **kwargs)
 
     def bound_data(self, data, initial):
```

**codex volley**: No blocking issues. Fix aligns field metadata with existing behavior (bound_data returns initial, has_changed returns False). Low regression risk.

**Gate result**: PASS — all 83 tests pass, including `test_readonly_field_has_changed`

**Trajectory**: Convergent success on first iteration

**Resolution**: H₀ confirmed — adding `kwargs.setdefault("disabled", True)` at line 58 fixes the failing test with no regressions.

---

# Audit: django__django-13741

## FAIL_TO_PASS
- test_readonly_field_has_changed (auth_tests.test_forms.ReadOnlyPasswordHashTest): **PASS** ✓

## PASS_TO_PASS regressions
None - all 83 tests passed.

## Pre-existing (not counted, confirmed against base capture)
None - all tests passed.

## Patch applied
```diff
diff --git a/django/contrib/auth/forms.py b/django/contrib/auth/forms.py
index b9eb33329f..9a6614a809 100644
--- a/django/contrib/auth/forms.py
+++ b/django/contrib/auth/forms.py
@@ -56,6 +56,7 @@ class ReadOnlyPasswordHashField(forms.Field):
 
     def __init__(self, *args, **kwargs):
         kwargs.setdefault("required", False)
+        kwargs.setdefault("disabled", True)
         super().__init__(*args, **kwargs)
 
     def bound_data(self, data, initial):
```

The fix adds `disabled=True` by default to `ReadOnlyPasswordHashField`, ensuring `has_changed()` always returns False for disabled fields (per Django's form field contract).

VERDICT: RESOLVED
RE-ENTER: none
