# Hypothesis graph: django__django-16139

## H₀: Relative URL doesn't account for to_field access pattern (abduction)

**Observation**: The test `test_link_to_password_reset_in_helptext_via_to_field` fails with:
```
AssertionError: '/admin/auth/user/testclient/password/' != '/admin/auth/user/1/password/'
```

**Root cause**: In `django/contrib/auth/forms.py:166`, the UserChangeForm.__init__ method formats the password help text with a relative URL `../password/`:

```python
password.help_text = password.help_text.format("../password/")
```

This relative URL works correctly when the UserAdmin change page is accessed via primary key (e.g., `/admin/auth/user/1/change/`), where `../password/` resolves to `/admin/auth/user/1/password/`.

However, when accessed via a to_field parameter (e.g., `/admin/auth/user/testclient/change/?_to_field=username`), the relative URL `../password/` resolves to `/admin/auth/user/testclient/password/` instead of the correct `/admin/auth/user/1/password/`.

The password change URL in Django admin always uses the primary key, not the to_field value. The relative path only goes up one level (replacing `change/` with `password/`), preserving whatever identifier was used in the URL path.

**Fix**: Replace the relative URL with an absolute-ish path that explicitly uses the instance's primary key:
```python
password.help_text = password.help_text.format(f"../../{self.instance.pk}/password/")
```

This goes up two levels (past both the identifier and `change/`), then explicitly constructs the path using the pk, ensuring it always resolves correctly regardless of how the change page was accessed.

**Confidence**: Deduction — 98%
- The test explicitly validates this exact scenario
- The error message shows the URL mismatch (testclient vs 1)
- The relative URL behavior is deterministic and traceable
- UserChangeForm is only used for existing users (UserCreationForm is used for new users), so `self.instance.pk` is always available

**Edit site**: `django/contrib/auth/forms.py:166`

## Craft Gate Loop

### Iteration 1: Draft and volley

**Action**: Drafted fix to replace `../password/` with `f"../../{self.instance.pk}/password/"` in `django/contrib/auth/forms.py` line 166.

**codex feedback**:
- Concerns raised about unsaved instances (pk=None)
- Concerns about URL escaping for custom user models with non-integer PKs
- Suggested using Django's URL reversing instead of string interpolation

**Decision**: Apply the fix and let the gate arbitrate. The concerns are valid edge cases, but UserChangeForm is specifically designed for editing existing users (separate UserCreationForm exists for new users).

### Iteration 2: Gate run

**Applied change**:
```diff
--- a/django/contrib/auth/forms.py
+++ b/django/contrib/auth/forms.py
@@ -163,7 +163,7 @@ class UserChangeForm(forms.ModelForm):
         super().__init__(*args, **kwargs)
         password = self.fields.get("password")
         if password:
-            password.help_text = password.help_text.format("../password/")
+            password.help_text = password.help_text.format(f"../../{self.instance.pk}/password/")
         user_permissions = self.fields.get("user_permissions")
         if user_permissions:
             user_permissions.queryset = user_permissions.queryset.select_related(
```

**Gate result**: ✅ PASS

```
Ran 87 tests in 0.145s
OK
```

**Status**: RESOLVED - FAIL_TO_PASS test now passes, no regressions in PASS_TO_PASS tests.

**Explanation**: The fix changes the password reset link from a single-level relative URL (`../password/`) to a two-level relative URL with explicit pk (`../../{self.instance.pk}/password/`). This ensures that:
1. When accessed via to_field (e.g., `/admin/auth/user/testclient/change/`), the link resolves to `/admin/auth/user/1/password/` (using pk, not username)
2. When accessed normally via pk (e.g., `/admin/auth/user/1/change/`), the link still resolves correctly to `/admin/auth/user/1/password/`

codex's concerns about unsaved instances and URL escaping were theoretical edge cases that didn't materialize in the test suite.

---

# Audit: django__django-16139

**Patch applied:** `django/contrib/auth/forms.py` — changed password reset link from `../password/` to `../../{self.instance.pk}/password/`

## FAIL_TO_PASS
- `test_link_to_password_reset_in_helptext_via_to_field (auth_tests.test_forms.UserChangeFormTest)`: **PASS** ✓

## PASS_TO_PASS regressions
None — all 86 PASS_TO_PASS tests remain passing.

## Pre-existing failures (not counted)
None

## Gate summary
Ran 87 tests in 0.145s — all passed.

The patch correctly fixes the password reset link to account for the `to_field` URL parameter by using the instance PK to navigate up two levels (`../../{pk}/password/`) instead of one (`../password/`).

VERDICT: RESOLVED
RE-ENTER: none
