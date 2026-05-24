# Hypothesis graph: django__django-15467

## H₀: Initial observation (abduction)
The test `test_radio_fields_foreignkey_formfield_overrides_empty_label` fails because the custom `empty_label` from `formfield_overrides` is overwritten when `radio_fields` is also specified.

**Evidence**: Test expects `ff.empty_label` to be "Custom empty label" but gets "None" instead.

## H₁: Root cause (deduction - 99%)
In `django/contrib/admin/options.py:272`, the `formfield_for_foreignkey` method unconditionally overwrites `kwargs["empty_label"]` when a field is in `radio_fields`:

```python
kwargs["empty_label"] = _("None") if db_field.blank else None
```

This happens AFTER `formfield_overrides` has already been merged into kwargs (line 167 in `formfield_for_dbfield`).

**Call path**:
1. Test calls `ma.formfield_for_dbfield(Inventory._meta.get_field("parent"), request=None)`
2. `formfield_for_dbfield` (line 149) merges formfield_overrides into kwargs (line 167):
   - `kwargs = {**self.formfield_overrides[db_field.__class__], **kwargs}`
   - At this point, `kwargs['empty_label'] = "Custom empty label"`
3. Calls `formfield_for_foreignkey(db_field, request, **kwargs)` (line 172)
4. Since "parent" is in `radio_fields`, line 272 unconditionally sets:
   - `kwargs["empty_label"] = _("None")` (because `db_field.blank` is True)
   - This overwrites the custom value from step 2

**Supporting code**:
- `django/contrib/admin/options.py:167` - formfield_overrides merged into kwargs
- `django/contrib/admin/options.py:272` - unconditional overwrite
- `tests/admin_widgets/models.py:83-84` - parent field has `blank=True`

## Edit site
`django/contrib/admin/options.py:272` - Only set `empty_label` if not already present in kwargs

## Gate Loop: craft iteration 1

**Diagnosis applied:** Line 272 in `django/contrib/admin/options.py` unconditionally overwrites `empty_label` when a ForeignKey is in `radio_fields`, even if a custom value was already provided via `formfield_overrides`.

**Fix:** Changed `kwargs["empty_label"] = _("None") if db_field.blank else None` to `kwargs.setdefault("empty_label", _("None") if db_field.blank else None)` to preserve any existing `empty_label` value in kwargs.

**codex review (pre-gate):** Approved. Confirmed the fix is correct and behavior change is intentional - explicit admin configuration should override the radio-field default.

**Gate result:** ✓ PASS
- FAIL_TO_PASS test `test_radio_fields_foreignkey_formfield_overrides_empty_label` now passes
- All 77 tests pass (14 skipped Selenium tests)

**Status:** RESOLVED

---

# Audit: django__django-15467

## FAIL_TO_PASS
- `test_radio_fields_foreignkey_formfield_overrides_empty_label`: **PASS** ✓

## PASS_TO_PASS regressions
**None** — all 77 tests passed (14 skipped Selenium tests).

## Pre-existing (not counted, confirmed against base capture)
**None** — the base capture showed all tests passing except the FAIL_TO_PASS test.

## Verdict Details

The patch successfully resolves the issue:
1. **Patch applied**: Changed line 272 in `django/contrib/admin/options.py` from `kwargs["empty_label"] = ...` to `kwargs.setdefault("empty_label", ...)`
2. **FAIL_TO_PASS test now passes**: The custom `empty_label` from `formfield_overrides` is preserved when `radio_fields` is specified
3. **Zero regressions**: All 76 other tests continue to pass
4. **Full gate output**: Ran 77 tests in 0.191s - OK (skipped=14)

The fix correctly uses `setdefault()` to only set the default empty_label if one hasn't already been provided via `formfield_overrides`, preserving the expected precedence of explicit admin configuration over implicit defaults.

VERDICT: RESOLVED
RE-ENTER: none
