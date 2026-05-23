# Hypothesis graph: django__django-16569

## H0: Initial diagnosis - Missing None check in add_fields() comparison

**Type**: Abduction → Deduction (confirmed by code trace)
**Status**: Active
**Confidence**: 99% (deduction from code reading and stack trace)

### Symptom
- Tests fail with `TypeError: '<' not supported between instances of 'NoneType' and 'int'`
- Stack trace shows: `formset.empty_form` → `add_fields(form, None)` → line 493 comparison
- Failure occurs when `can_delete=True` and `can_delete_extra=False`

### Root cause
File: `django/forms/formsets.py`, line 493

```python
if self.can_delete and (self.can_delete_extra or index < initial_form_count):
```

When `empty_form` property calls `add_fields(form, None)`:
- `index` is `None`
- `can_delete` is `True`
- `can_delete_extra` is `False`
- Python evaluates `None < initial_form_count`, which raises TypeError

### Evidence
1. Line 267 in formsets.py: `empty_form` property calls `self.add_fields(form, None)`
2. Line 480 in formsets.py: ordering field logic correctly checks `if index is not None and index < initial_form_count:`
3. Line 493 in formsets.py: deletion field logic missing the None check
4. Git commit 162765d6c3 (2020-06-19): introduced `can_delete_extra` feature but didn't add None check

### Edit sites
- `django/forms/formsets.py:493` - Add `index is not None and` before `index < initial_form_count`
  - Change: `if self.can_delete and (self.can_delete_extra or index < initial_form_count):`
  - To: `if self.can_delete and (self.can_delete_extra or (index is not None and index < initial_form_count)):`

### Test verification
- `test_disable_delete_extra_formset_forms` checks that DELETE field is NOT in `empty_form.fields` when `can_delete_extra=False`
- Extra forms (index >= initial_form_count or index is None) should not have DELETE field when `can_delete_extra=False`
- Initial forms (index < initial_form_count) should have DELETE field when `can_delete=True`


## Gate Loop Node 1 (RESOLVED)

**Iteration**: 1 of 8
**Status**: PASS - Gate green

**Applied fix**: Added None check to deletion field condition in `django/forms/formsets.py` lines 493-495:
```python
if self.can_delete and (
    self.can_delete_extra or (index is not None and index < initial_form_count)
):
```

**Pre-gate codex review**: No behavioral bugs. Fix correctly prevents TypeError when `empty_form` calls `add_fields(form, None)`. Logic mirrors the existing ordering field pattern at line 480.

**Gate result**: 
- All 157 tests passed in 0.381s
- Both FAIL_TO_PASS tests passed:
  - test_disable_delete_extra_formset_forms (forms_tests.tests.test_formsets.FormsFormsetTestCase)
  - test_disable_delete_extra_formset_forms (forms_tests.tests.test_formsets.Jinja2FormsFormsetTestCase)

**Trajectory**: Convergent (resolved) - Fix addressed the root cause directly. No regressions.

**Evidence**: The recon diagnosis was accurate. The fix adds the missing None check before comparing `index < initial_form_count`, preventing the TypeError when `index=None` while preserving correct behavior:
- Initial forms (index 0..N-1): get DELETE field ✓
- Extra forms (index N..M): don't get DELETE field (when can_delete_extra=False) ✓  
- empty_form (index None): doesn't crash, doesn't get DELETE field ✓


---

# Audit: django__django-16569

## Patch confirmed live
```
 django/forms/formsets.py | 4 +++-
 1 file changed, 3 insertions(+), 1 deletion(-)
```

## FAIL_TO_PASS
- test_disable_delete_extra_formset_forms (forms_tests.tests.test_formsets.FormsFormsetTestCase.test_disable_delete_extra_formset_forms): **PASS** ✓
- test_disable_delete_extra_formset_forms (forms_tests.tests.test_formsets.Jinja2FormsFormsetTestCase.test_disable_delete_extra_formset_forms): **PASS** ✓

## PASS_TO_PASS regressions
None. All 157 tests in the suite passed.

## Pre-existing failures (not counted)
None. The fail-on-base capture showed all tests passing (the output was truncated but ended with `OK`).

## Analysis
The patch adds a `index is not None` guard before the `index < initial_form_count` comparison on line 493 of `django/forms/formsets.py`. This prevents a TypeError when `add_fields()` is called with `index=None` (via the `empty_form` property) and `can_delete=True` with `can_delete_extra=False`.

The fix mirrors the pattern already present at line 480 for the ordering field. The change is minimal (3 insertions, 1 deletion) and surgical—it only affects the deletion field logic path and correctly preserves the intended behavior:
- Initial forms still get the DELETE field when `can_delete=True`
- Extra forms don't get the DELETE field when `can_delete_extra=False`
- The `empty_form` with `index=None` no longer crashes and correctly omits the DELETE field

All 157 formset tests pass cleanly with zero regressions.

VERDICT: RESOLVED
RE-ENTER: none
