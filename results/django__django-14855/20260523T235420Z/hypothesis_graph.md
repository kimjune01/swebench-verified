# Hypothesis graph: django__django-14855

## H₁: Missing current_app parameter in get_admin_url (ACTIVE)

**Type**: Deduction  
**Confidence**: 99%  
**Date**: 2026-05-23

### Observation

Test failure: `test_readonly_foreignkey_links_custom_admin_site` expects URLs with custom admin site namespace `/test_admin/admin5/...` but receives `/admin/...` URLs.

### Hypothesis

The `AdminReadonlyField.get_admin_url()` method (django/contrib/admin/helpers.py:206-214) generates URLs for readonly ForeignKey fields using a hardcoded `'admin:'` namespace and does not pass the `current_app` parameter to `reverse()`. This prevents the URL resolver from using the current admin site's namespace.

### Evidence

1. **Code path**: `helpers.py:212` - `url = reverse(url_name, args=[quote(remote_obj.pk)])` lacks `current_app` parameter
2. **Pattern elsewhere**: All similar `reverse()` calls in `options.py` include `current_app=self.admin_site.name` (lines 1194, 1313, 1325, 1342, 1347, 1462, 1469, 1543)
3. **Access confirmed**: `self.model_admin.admin_site.name` is available (chain: AdminForm → Fieldset → Fieldline → AdminReadonlyField all pass `model_admin`)
4. **Git history**: Feature added in commit b790883065 without custom admin site support

### Predicted fix

Add `current_app=self.model_admin.admin_site.name` parameter to the `reverse()` call on line 212.

### Edit site

- `django/contrib/admin/helpers.py:212` - Add current_app parameter to reverse() call

## craft: Gate Loop

### Iteration 1: Initial fix applied

**Diagnosis**: Missing `current_app` parameter in `get_admin_url()` method in `django/contrib/admin/helpers.py`

**Fix applied**: Added `current_app=self.model_admin.admin_site.name if self.model_admin else None` to the `reverse()` call in `get_admin_url()` method.

**codex feedback**: Guard against `model_admin=None` to avoid AttributeError

**Diff**:
```diff
--- a/django/contrib/admin/helpers.py
+++ b/django/contrib/admin/helpers.py
@@ -211,7 +211,8 @@ class AdminReadonlyField:
             remote_field.model._meta.model_name,
         )
         try:
-            url = reverse(url_name, args=[quote(remote_obj.pk)])
+            current_app = self.model_admin.admin_site.name if self.model_admin else None
+            url = reverse(url_name, args=[quote(remote_obj.pk)], current_app=current_app)
             return format_html('<a href="{}">{}</a>', url, remote_obj)
         except NoReverseMatch:
             return str(remote_obj)
```

**Gate result**: ✅ PASS - All 345 tests passed, including `test_readonly_foreignkey_links_custom_admin_site`

**Trajectory**: Convergent (green) - Fix correctly addresses the root cause

---

## Audit: django__django-14855

**Date**: 2026-05-23

### Patch verification
Confirmed patch is live: `django/contrib/admin/helpers.py` modified (+2/-1 lines)

### FAIL_TO_PASS
- `test_readonly_foreignkey_links_custom_admin_site (admin_views.tests.ReadonlyTest)`: **PASS** ✅

### PASS_TO_PASS regressions
**None** - All 345 tests passed

### Pre-existing failures (confirmed against base capture)
**None** - Clean gate run

### Full gate result
```
Ran 345 tests in 19.557s
OK (skipped=15)
```

### Classification
- ✅ FAIL_TO_PASS test now passes
- ✅ Zero regressions introduced
- ✅ All PASS_TO_PASS tests continue passing
- ✅ Patch correctly passes `current_app` to `reverse()` to respect custom admin site namespace

**VERDICT**: RESOLVED  
**RE-ENTER**: none
