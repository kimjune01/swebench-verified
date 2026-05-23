# Hypothesis graph: django__django-16100

## Hypothesis H1: Missing transaction wrapper in changelist_view list_editable processing

**Type**: Abduction → Deduction (traced through code)
**Status**: Active
**Confidence**: 98%

### Failure Analysis
The test `test_list_editable_atomicity` creates two Swallow objects with initial values (a: load=4, speed=1; b: load=2, speed=2), then POSTs updated values (a: load=9.0, speed=3.0; b: load=5.0, speed=1.0) to the changelist. When `ModelAdmin.log_change` is mocked to raise a `DatabaseError`:
- Expected: All changes are rolled back, original values preserved
- Actual: Changes are committed despite the error (a.load=9.0 instead of 4)
- Error: `AssertionError: 9.0 != 4` at line 431 of test

### Root Cause
The `changelist_view` method in `django/contrib/admin/options.py` (lines 2012-2037) processes list_editable formset submissions without transaction protection. The processing loop:

```python
if formset.is_valid():
    changecount = 0
    for form in formset.forms:
        if form.has_changed():
            obj = self.save_form(request, form, change=True)
            self.save_model(request, obj, form, change=True)
            self.save_related(request, form, formsets=[], change=True)
            change_msg = self.construct_change_message(request, form, None)
            self.log_change(request, obj, change_msg)  # ← DatabaseError injected here
            changecount += 1
```

When processing multiple forms, if an error occurs at any point (e.g., during `log_change` for the first object), the previously saved objects remain committed to the database. There is no transaction to roll back the partial changes.

### Supporting Evidence
1. `django/contrib/admin/options.py:2012-2037` - The `if formset.is_valid():` block contains database writes (save_form, save_model, save_related, log_change) without transaction wrapping
2. `django/contrib/admin/options.py:1745` - `changeform_view` wraps its processing with `transaction.atomic(using=router.db_for_write(self.model))`
3. `django/contrib/admin/options.py:2102` - `delete_view` wraps its processing with `transaction.atomic(using=router.db_for_write(self.model))`
4. `django/contrib/admin/options.py:39` - Both `router` and `transaction` are already imported
5. Test scenarios confirm partial saves: when log_change fails for object 1 OR object 2, the database shows committed changes instead of rollback

### Edit Sites
**File**: `django/contrib/admin/options.py`
**Line range**: 2012-2037

**Change**: Wrap the `if formset.is_valid():` block with `transaction.atomic(using=router.db_for_write(self.model))` to ensure all database operations in the list_editable processing are atomic. This follows the established pattern used in `changeform_view` and `delete_view`.

The transaction should encompass:
- The entire formset processing loop (lines 2014-2024)
- The success message (lines 2026-2033)
- The redirect (line 2035)

This ensures that if any operation fails (save_form, save_model, save_related, log_change, or message_user), all changes are rolled back atomically.

### Reasoning Mode
**Deduction** - Traced execution path from failing test through the code:
1. Test POSTs to changelist URL → routes to `changelist_view`
2. `changelist_view` checks for list_editable POST → enters block at line 2002
3. Formset is validated → enters block at line 2012
4. Loop iterates over forms, saving each object and logging changes
5. No transaction wrapper exists around this block
6. When `log_change` raises DatabaseError, prior saves are not rolled back
7. Test confirms: objects have new values instead of original values


## craft gate-loop iteration 1

**Diagnosis**: Django admin's changelist view doesn't wrap list_editable processing in a transaction. When saving multiple edited objects, if an error occurs (like during `log_change`), previously saved changes persist instead of rolling back.

**Edit site**: Lines 2012-2023 in `django/contrib/admin/options.py` - the formset processing loop that calls `save_form`, `save_model`, `save_related`, and `log_change`.

**Applied fix**: Wrapped the save/log loop with `transaction.atomic(using=router.db_for_write(self.model))`, following the same pattern used in `changeform_view` and `delete_view`. Per codex feedback, kept the transaction scope tight - only the DB operations (save loop), not the message/redirect.

**codex volley**: Approved the approach, suggested tightening scope to exclude message_user and redirect from the transaction block to avoid unnecessary session work inside the DB transaction.

**Gate result**: PASS
- test_list_editable_atomicity: ✓ ok
- All 71 tests in admin_changelist.tests passed

**Status**: RESOLVED - FAIL_TO_PASS test now passes, transaction rollback works correctly for list_editable errors.


## Audit: django__django-16100

### Patch verification
Patch is live in tree: `django/contrib/admin/options.py` (9 insertions, 8 deletions)

### Gate results
Ran 71 tests in 0.684s - OK (skipped=7)

### FAIL_TO_PASS
- test_list_editable_atomicity (admin_changelist.tests.ChangeListTests): **PASS** ✓

### PASS_TO_PASS regressions
**None** - All 64 PASS_TO_PASS tests passed without regression:
- All GetAdminLogTests tests: PASS
- test_changelist_search_form_validation: PASS
- test_changelist_view_list_editable_changed_objects_uses_filter: PASS
- test_clear_all_filters_link: PASS
- test_clear_all_filters_link_callable_filter: PASS
- All other ChangeListTests: PASS

### Pre-existing failures
**None** - No pre-existing failures detected. All non-Selenium tests passed.

### Final classification
The craft patch successfully:
1. Wrapped the list_editable processing loop in `transaction.atomic(using=router.db_for_write(self.model))`
2. Ensured atomicity: when `log_change` or any other operation fails during multi-object edits, all changes roll back
3. Fixed the FAIL_TO_PASS test without introducing any regressions
4. Follows established patterns from `changeform_view` and `delete_view`

VERDICT: RESOLVED
RE-ENTER: none
