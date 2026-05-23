# Hypothesis graph: django__django-16527

## H₀ (initial observation - abduction)
The test `test_submit_row_save_as_new_add_permission_required` fails because `show_save_as_new` is True when it should be False for a user with only change permission (no add permission).

Error: `AssertionError: True is not False` at line 52 of tests/admin_views/test_templatetags.py

## Root Cause Hypothesis (deduction - 98% confidence)

**What:** The `show_save_as_new` flag in `django/contrib/admin/templatetags/admin_modify.py` (lines 102-105) does not check for `has_add_permission`.

**Why:** The "save as new" action creates a new object (it's an add operation), but the template tag only checks:
- `not is_popup`
- `has_change_permission` 
- `change`
- `save_as`

It's missing the `has_add_permission` check.

**Evidence:** 
- `django/contrib/admin/templatetags/admin_modify.py:102-105` - current condition lacks add permission check
- `django/contrib/admin/options.py:1756-1763` - backend correctly checks add permission when processing `_saveasnew` POST
- `tests/admin_views/test_templatetags.py:38-52` - test verifies user with only change permission should NOT see the button
- `tests/admin_views/test_templatetags.py:54-67` - test verifies user with both add and change permission SHOULD see the button

**Why this matters:** The backend at `django/contrib/admin/options.py:1756-1763` already enforces add permission when processing the save_as_new action, but the frontend template tag shows the button to users who don't have permission to use it, creating a poor UX (users see a button that will fail with PermissionDenied when clicked).

**Similar patterns in same file:**
- `can_save_and_add_another` (lines 80-86) correctly checks `has_add_permission` because "save and add another" is also an add operation

**Fix:** Add `and has_add_permission` to the condition at line 102.

Confidence: **deduction - 98%** (traced the code path, verified backend behavior, identified the missing check)

## Gate iteration 1 (RESOLVED)

**Drafted fix:** Added `and has_add_permission` to the `show_save_as_new` condition at line 102-105 in `django/contrib/admin/templatetags/admin_modify.py`.

**Codex review:** No blocking issues. Fix matches backend permission model. Test coverage already exists in FAIL_TO_PASS.

**Applied diff:**
```diff
--- a/django/contrib/admin/templatetags/admin_modify.py
+++ b/django/contrib/admin/templatetags/admin_modify.py
@@ -99,6 +99,7 @@ def submit_row(context):
             ),
             "show_save_as_new": not is_popup
             and has_change_permission
+            and has_add_permission
             and change
             and save_as,
             "show_save_and_add_another": can_save_and_add_another,
```

**Gate result:** ✅ PASS — all 7 tests pass, including `test_submit_row_save_as_new_add_permission_required`.

**Outcome:** RESOLVED. The fix correctly enforces add permission requirement for the "Save as new" button, matching backend behavior.

---

# Audit: django__django-16527

## FAIL_TO_PASS
- `test_submit_row_save_as_new_add_permission_required`: **PASS** ✓

## PASS_TO_PASS regressions
None - all PASS_TO_PASS tests pass:
- `test_choice_links`: PASS ✓
- `test_choice_links_datetime`: PASS ✓
- `test_override_change_form_template_tags`: PASS ✓
- `test_override_change_list_template_tags`: PASS ✓
- `test_override_show_save_and_add_another`: PASS ✓
- `test_submit_row`: PASS ✓

## Pre-existing failures
None (baseline capture was incomplete, but all 7 tests in the suite passed)

## Summary
The patch successfully adds `has_add_permission` to the `show_save_as_new` condition in `django/contrib/admin/templatetags/admin_modify.py`. The FAIL_TO_PASS test now passes, confirming that users without add permission no longer see the "Save as new" button. All PASS_TO_PASS tests continue to pass with no regressions.

VERDICT: RESOLVED
RE-ENTER: none
