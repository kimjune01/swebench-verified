# Hypothesis graph: django__django-16612

## Recon Pass 1

**Date:** 2026-05-23  
**Mode:** abduction

### H₀: Baseline failure observation
The tests fail because `AdminSite.catch_all_view()` redirects to a URL with a trailing slash but drops the query string. The tests expect `/admin/admin_views/article/?id=1` but get `/admin/admin_views/article/`.

**Error:**
```
AssertionError: '/test_admin/admin/admin_views/article/' != '/test_admin/admin/admin_views/article/?id=1'
```

### Suspect Set
- `django/contrib/admin/sites.py` lines 447-457: `catch_all_view` method
- Specifically line 456: `return HttpResponsePermanentRedirect("%s/" % request.path)`

### Root Cause
The `catch_all_view` method at line 456 uses `request.path` for building the redirect URL. The `request.path` attribute only contains the path portion of the URL without query strings. When a URL like `/admin/article?id=1` (missing trailing slash) is redirected with `APPEND_SLASH=True`, the code constructs `/admin/article/` but loses the `?id=1` query string.

**Confidence:** deduction — 98%

**Supporting evidence:**
- `django/contrib/admin/sites.py:456` — `return HttpResponsePermanentRedirect("%s/" % request.path)`
  - Uses `request.path` which excludes query strings
- `django/middleware/common.py:83` — Django's `CommonMiddleware` handles the same scenario using `request.get_full_path(force_append_slash=True)` which includes query strings
- `django/http/request.py:183-193` — `_get_full_path` implementation shows it constructs URLs as: `path + "/" + "?" + QUERY_STRING`

**Historical context:**
- Commit ba31b01034 (2021) introduced `catch_all_view` for #31747 without query string handling
- Commit f7691d4812 (2021) fixed SCRIPT_NAME handling (#32754) by changing from `request.path_info` to `request.path`, but still didn't add query string support

### Edit Sites
- `django/contrib/admin/sites.py` line 456: Change `return HttpResponsePermanentRedirect("%s/" % request.path)` to `return HttpResponsePermanentRedirect(request.get_full_path(force_append_slash=True))`
  - This mirrors the pattern used in `CommonMiddleware.get_full_path_with_slash()`
  - `get_full_path(force_append_slash=True)` appends the trailing slash AND preserves the query string
  - Uses `request.path` internally (respecting SCRIPT_NAME) and appends `request.META['QUERY_STRING']`

### Rejected Hypotheses
None — the root cause is clear from code inspection and confirmed by the middleware implementation.

### Open Questions
- Should `escape_leading_slashes` (from `django.utils.http`) be added for security? The middleware uses it to prevent scheme-relative URL attacks. However, the current code doesn't use it, and the tests don't require it.

## Craft gate-loop node 1

**Hypothesis:** The `catch_all_view` redirect drops query strings because it uses `request.path` instead of `request.get_full_path(force_append_slash=True)`.

**Edit applied:**
```diff
--- a/django/contrib/admin/sites.py
+++ b/django/contrib/admin/sites.py
@@ -453,7 +453,7 @@ class AdminSite:
             pass
         else:
             if getattr(match.func, "should_append_slash", True):
-                return HttpResponsePermanentRedirect("%s/" % request.path)
+                return HttpResponsePermanentRedirect(request.get_full_path(force_append_slash=True))
     raise Http404
```

**Codex pre-gate review:** Confirmed fix is correct. Uses Django's existing `get_full_path(force_append_slash=True)` API which appends slash before query string and preserves the query parameters. Matches pattern from CommonMiddleware.

**Gate result:** ✅ PASS - All 364 tests passed (23 skipped)
- `test_missing_slash_append_slash_true_query_string` ✅ 
- `test_missing_slash_append_slash_true_script_name_query_string` ✅

**Trajectory:** Convergent success - both FAIL_TO_PASS tests now pass, no regressions.

**Resolution:** Single-line fix confirmed. Query strings are now preserved when redirecting admin URLs with missing trailing slashes.

## Audit: django__django-16612

**Date:** 2026-05-23  
**Audit Phase:** Final verification against full gate

### Patch Verification
✅ Patch present: 1 file changed, 1 insertion, 1 deletion
```diff
django/contrib/admin/sites.py | 2 +-
```

### FAIL_TO_PASS Results
- ✅ test_missing_slash_append_slash_true_query_string: PASS
- ✅ test_missing_slash_append_slash_true_script_name_query_string: PASS

### PASS_TO_PASS Regressions
None — all 364 tests passed (23 skipped for missing browser drivers).

Sample PASS_TO_PASS verification:
- ✅ test_explicitly_provided_pk: PASS
- ✅ test_implicitly_generated_pk: PASS
- ✅ test_secure_view_shows_login_if_not_logged_in: PASS
- ✅ test_staff_member_required_decorator_works_with_argument: PASS
- ✅ test_generic_content_object_in_list_display: PASS
- ✅ test_lang_name_present: PASS

### Pre-existing Failures
None — baseline capture showed clean test suite on unpatched code.

### Gate Summary
```
Ran 364 tests in 16.631s
OK (skipped=23)
```

**Final Status:** All FAIL_TO_PASS tests now pass. Zero regressions. The fix correctly preserves query strings when redirecting admin URLs with missing trailing slashes by using `request.get_full_path(force_append_slash=True)` instead of manually concatenating `request.path + "/"`.

### Kill Report
Not applicable — patch resolves the issue cleanly.
