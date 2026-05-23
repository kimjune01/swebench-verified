# Hypothesis graph: django__django-12193

## Hypothesis H0 (abduction)
**Claim:** The tests fail because CheckboxInput.get_context() mutates the attrs dict parameter.
**Evidence:** Test assertion `self.assertIs(attrs['checked'], False)` fails with `AssertionError: True is not False`
**Status:** ACTIVE

## Hypothesis H1 (deduction)
**Claim:** CheckboxInput.get_context() at line 527 directly mutates the attrs parameter by setting `attrs['checked'] = True`, violating immutability expectations.
**Evidence:**
- `django/forms/widgets.py:523-527` — CheckboxInput.get_context() code
- `django/forms/widgets.py:527` — Direct mutation: `attrs['checked'] = True`
- `tests/forms_tests/widget_tests/test_checkboxinput.py:95-96` — Test shows attrs mutated from False to True
**Confidence:** 99% (deduction)
**Status:** ACTIVE

## Hypothesis H2 (deduction)
**Claim:** Other widgets avoid this issue by copying attrs before modification.
**Evidence:**
- `django/forms/widgets.py:350` — Pattern: `widget_attrs = final_attrs.copy()`
- `django/forms/widgets.py:249` — build_attrs() creates new dicts: `{**base_attrs, **(extra_attrs or {})}`
**Confidence:** 99% (deduction)
**Status:** SUPPORTING

## Hypothesis H3 (deduction)
**Claim:** The mutation causes all widgets in SplitArrayWidget after the first True value to be checked.
**Evidence:**
- `django/contrib/postgres/forms/array.py:137-149` — SplitArrayWidget reuses final_attrs across loop iterations
- When id is None, final_attrs is the same object in every iteration
- After first CheckboxInput.get_context(True, final_attrs) sets attrs['checked']=True, all subsequent iterations see this mutation
**Confidence:** 95% (deduction)
**Status:** SUPPORTING


## craft gate-loop iteration 1

**Fix applied:** Modified `CheckboxInput.get_context()` at django/forms/widgets.py:523-528 to create a copy of attrs before modifying it, preventing mutation of the caller's dict.

```python
def get_context(self, name, value, attrs):
    if self.check_test(value):
        attrs = attrs.copy() if attrs is not None else {}
        attrs['checked'] = True
    return super().get_context(name, value, attrs)
```

**codex feedback (pre-gate):** Suggested using `.copy()` pattern instead of dict unpacking for consistency with Django codebase style.

**Gate result:** ✅ PASS
- test_get_context_does_not_mutate_attrs: ok
- All 122 tests passed (110 skipped PostgreSQL tests)

**Trajectory:** Convergent success — fix correctly prevents mutation by creating new dict before modification.

## Audit: django__django-12193

**Patch status:** Live in tree (django/forms/widgets.py modified, 1 insertion, 2 deletions)

**Gate execution:** Full test suite ran successfully

### FAIL_TO_PASS
- `test_get_context_does_not_mutate_attrs`: **PASS** ✓

### PASS_TO_PASS (all passing, no regressions)
- `test_render_check_exception`: ok
- `test_render_check_test`: ok
- `test_render_empty`: ok
- `test_render_false`: ok
- `test_render_int`: ok
- `test_render_none`: ok
- `test_render_true`: ok
- `test_render_value`: ok
- `test_value_from_datadict`: ok
- `test_value_from_datadict_string_int`: ok
- `test_value_omitted_from_data`: ok

### Pre-existing failures (not counted)
None

### Classification summary
- All FAIL_TO_PASS tests now pass: ✓
- PASS_TO_PASS regressions: 0
- Total test result: 122 tests ran, OK (110 skipped PostgreSQL tests)

The fix successfully prevents mutation of the attrs parameter by creating a copy before modification, resolving the issue without introducing any regressions.
