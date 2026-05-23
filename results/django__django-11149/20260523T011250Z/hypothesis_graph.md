# Hypothesis graph: django__django-11149
# Hypothesis Graph: django__django-11149

## H₀: Initial symptom (abduction)
The tests `test_inline_add_m2m_view_only_perm` and `test_inline_change_m2m_view_only_perm` fail because `has_add_permission` returns `True` instead of `False` when a user has only `view_book` permission on a ManyToManyField inline.

**Evidence**: Test failures at `tests/admin_inlines/tests.py:646` and `tests/admin_inlines/tests.py:693`
```
AssertionError: True is not False
```

**Mode**: Abduction (observed symptom)

## H₁: Root cause identified (deduction - 98%)
In `django/contrib/admin/options.py` lines 2114-2138, the `InlineModelAdmin` class methods `has_add_permission`, `has_change_permission`, and `has_delete_permission` all incorrectly return `self.has_view_permission(request, obj)` for auto-created ManyToMany intermediate models.

**Problem**: The methods delegate to `has_view_permission`, which returns `True` if the user has either `view` OR `change` permission on the related model. This means:
- User with only `view_book` permission → `has_view_permission` returns `True` → `has_add_permission` returns `True` (WRONG!)
- Should be: User with only `view_book` permission → `has_add_permission` should return `False`

**Supporting evidence**:
1. `django/contrib/admin/options.py:2114-2120` - `has_add_permission` returns `self.has_view_permission(request, obj)` for auto-created models
2. `django/contrib/admin/options.py:2123-2129` - `has_change_permission` returns `self.has_view_permission(request, obj)` for auto-created models
3. `django/contrib/admin/options.py:2132-2138` - `has_delete_permission` returns `self.has_view_permission(request, obj)` for auto-created models
4. `django/contrib/admin/options.py:2140-2153` - `has_view_permission` returns `True` if user has `view` OR `change` permission on the related model

**Test evidence confirms expected behavior**:
- `tests/admin_inlines/tests.py` line ~678: User with `change_book` permission SHOULD have add/change/delete/view on inline
- `tests/admin_inlines/tests.py` line ~660: User with only `add_book` permission should NOT see the inline at all (needs change permission)
- `tests/admin_inlines/tests.py` line ~639: User with only `view_book` permission should only have view permission, NOT add/change/delete

**Conclusion**: For auto-created m2m intermediate models, add/change/delete operations should require `change` permission on the related model, not just `view` permission.

**Mode**: Deduction (traced code execution path, identified exact logic error)

## Gate Loop - Craft Phase

### Iteration 1: Initial Fix

**Applied changes:**
Modified three permission methods in `django/contrib/admin/options.py`:
- `has_add_permission` (lines 2114-2125)
- `has_change_permission` (lines 2127-2138)  
- `has_delete_permission` (lines 2140-2151)

Changed each method to check for `change` permission specifically on the related model instead of delegating to `has_view_permission` (which checks for view OR change).

**Implementation approach:**
- Replicated the target model lookup logic from `has_view_permission`
- Check only for `change` permission: `request.user.has_perm('%s.%s' % (opts.app_label, get_permission_codename('change', opts)))`
- Updated comments to reflect that mutating M2M relationships requires `change` permission

**Gate result:** ✅ PASS
- All 54 tests passed (6 skipped Selenium tests)
- Both FAIL_TO_PASS tests now pass:
  - `test_inline_add_m2m_view_only_perm` 
  - `test_inline_change_m2m_view_only_perm`

**Codex feedback (pre-gate):**
Noted code duplication across three methods and suggested extracting helper methods. This is a maintenance/style concern, not a correctness issue. The gate confirmed the fix is correct.

**Trajectory:** Convergent-resolved (first attempt success)


## Audit: django__django-11149

**Patch status:** Live (36 lines changed in django/contrib/admin/options.py)

**Gate execution:** Full suite run complete (54 tests, 6 skipped Selenium)

### FAIL_TO_PASS
- `test_inline_add_m2m_view_only_perm`: **PASS** ✓
- `test_inline_change_m2m_view_only_perm`: **PASS** ✓

### PASS_TO_PASS regressions
None. All specified PASS_TO_PASS tests remain passing:
- `test_immutable_content_type` (Regression for #9362): ok
- `test_deleting_inline_with_protected_delete_does_not_validate`: ok
- `test_all_inline_media`: ok
- `test_inline_media_only_base`: ok
- `test_inline_media_only_inline`: ok
- `test_inline_add_fk_add_perm`: ok
- `test_inline_add_fk_noperm`: ok
- `test_inline_add_m2m_add_perm`: ok
- `test_inline_add_m2m_noperm`: ok
- `test_inline_change_fk_add_change_perm`: ok
- `test_inline_change_fk_add_perm`: ok

### Pre-existing (not counted)
None. The fail-on-base capture showed the two FAIL_TO_PASS tests failing (as expected), and all others passing.

### Classification
All FAIL_TO_PASS tests now pass. Zero PASS_TO_PASS regressions introduced. The fix correctly restricts add/change/delete permissions on auto-created M2M inline models to require `change` permission on the target model, while preserving view-only access with just `view` permission.

