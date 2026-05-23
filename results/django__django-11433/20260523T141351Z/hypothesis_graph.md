# Hypothesis graph: django__django-11433

## H₀ (Initial Abduction - 2026-05-23)

**Observation:** Test `test_default_not_populated_on_non_empty_value_in_cleaned_data` fails with:
- Expected: pub.mode = 'de' (value set in cleaned_data)
- Actual: pub.mode = 'di' (model field's default value)

**Hypothesis:** The `construct_instance()` function in `django/forms/models.py` (lines 50-52) skips setting values from `cleaned_data` when a field has a default value and was omitted from POST data, even if `cleaned_data` contains a non-empty value for that field.

**Evidence:**
- Line 42-43: Field IS in cleaned_data, so not skipped
- Line 50-52: Condition checks `f.has_default()` AND `value_omitted_from_data()` → both True → skips to next field
- Line 59: `f.save_form_data()` never called, so cleaned_data['mode'] = 'de' is ignored
- Model instance retains default value 'di'

**Root Cause:** The condition doesn't check whether the value in `cleaned_data` is empty before deciding to skip. It should only leave the default if the `cleaned_data` value is empty.

**Confidence:** Deduction - 95%
- Code path traced from test → _post_clean → construct_instance
- Exact line identified where skip occurs
- Logic matches observed failure


## Gate loop iteration 1

**Action**: Applied fix to `django/forms/models.py` lines 49-56 based on recon diagnosis
- Added `form_field = form.fields[f.name]` variable for cleaner access
- Modified condition to check three things before skipping:
  1. `f.has_default()` - field has a default
  2. `form_field.widget.value_omitted_from_data(...)` - value was omitted from POST
  3. `cleaned_data[f.name] in form_field.empty_values` - cleaned_data value is empty

**Codex review**: Approved semantics. Suggested style improvement (use `form.fields[f.name]` directly instead of `form[f.name].field`), which was incorporated.

**Gate result**: PASS - all 144 tests pass including `test_default_not_populated_on_non_empty_value_in_cleaned_data`

**Trajectory**: Convergent (immediate resolution)

**Root cause confirmed**: The original code skipped setting values from `cleaned_data` when a field had a default AND was omitted from POST data, without checking if the `cleaned_data` value was empty. The fix ensures defaults are only used when the `cleaned_data` value is actually empty.


## Audit: django__django-11433

### FAIL_TO_PASS
- `test_default_not_populated_on_non_empty_value_in_cleaned_data (model_forms.tests.ModelFormBaseTest)`: **PASS** ✓

### PASS_TO_PASS regressions
None - all 144 tests passed.

### Pre-existing failures (not counted)
None.

### Verdict
All FAIL_TO_PASS tests now pass. Zero PASS_TO_PASS regressions. The patch correctly fixes the issue where `construct_instance()` was skipping non-empty `cleaned_data` values when a field had a default and was omitted from POST data. The fix adds a check to ensure the `cleaned_data` value is actually empty before skipping.

VERDICT: RESOLVED
RE-ENTER: none

