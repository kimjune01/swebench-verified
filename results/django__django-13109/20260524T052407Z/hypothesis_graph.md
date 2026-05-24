# Hypothesis graph: django__django-13109
## H₀: Initial Hypothesis (abduction)

**Status**: ACTIVE  
**Mode**: Deduction  
**Confidence**: 95%

The tests fail because ForeignKey.validate() uses the default manager instead of the base manager to check if a foreign key value exists. When a model has a custom default manager that filters records (e.g., `archived=False`), validation incorrectly fails for valid database records that are filtered out by the manager.

**Evidence**:
- `django/db/models/fields/related.py:917` - Uses `_default_manager.using(using).filter()`
- AuthorManager and WriterManager both filter by `archived=False`
- Tests create archived records and expect validation to pass
- Error: 'author instance with id 1 does not exist.' (but it does exist in DB)

**Root cause**:
Line 917 in ForeignKey.validate() queries using `self.remote_field.model._default_manager` which respects manager filters. Referential integrity validation should check database-level existence, not application-level visibility.

**Edit site**:
- `django/db/models/fields/related.py` line 917: Change from `_default_manager` to `_base_manager`

**Supporting code**:
```python
# Line 909-920: ForeignKey.validate()
def validate(self, value, model_instance):
    if self.remote_field.parent_link:
        return
    super().validate(value, model_instance)
    if value is None:
        return

    using = router.db_for_read(self.remote_field.model, instance=model_instance)
    qs = self.remote_field.model._default_manager.using(using).filter(  # <-- LINE 917: ISSUE
        **{self.remote_field.field_name: value}
    )
    qs = qs.complex_filter(self.get_limit_choices_to())
    if not qs.exists():
        raise exceptions.ValidationError(...)
```

**Test reproduction**:
Both failing tests create archived records (filtered out by default manager) and expect validation to succeed:
1. `test_FK_validates_using_base_manager`: Direct model validation via `article.full_clean()`
2. `test_validate_foreign_key_to_model_with_overridden_manager`: Form validation where queryset is explicitly set to `_base_manager`


## Craft gate loop (iteration 1)

**Applied fix:** Changed `_default_manager` to `_base_manager` in ForeignKey.validate() at django/db/models/fields/related.py:917

**codex review (pre-gate):** No functional problem. The change is correct — FK existence validation should use `_base_manager` to check database-level referential integrity, not application-level manager filters. Forms still validate against their own queryset before model validation.

**Gate result:** ✅ PASS
- Ran 173 tests in 0.355s
- All tests passed, including both FAIL_TO_PASS tests:
  - test_FK_validates_using_base_manager (validation.tests.BaseModelValidationTests)
  - test_validate_foreign_key_to_model_with_overridden_manager (model_forms.tests.ModelFormBasicTests)

**Resolution:** The single-line fix from recon was correct and sufficient. No regressions.

## Audit: django__django-13109

**Patch verification**: Confirmed 1 file changed (django/db/models/fields/related.py, 1 insertion, 1 deletion)

**Gate execution**: Ran 173 tests in 0.358s - ALL PASSED

### FAIL_TO_PASS
- `test_FK_validates_using_base_manager (validation.tests.BaseModelValidationTests)`: **PASS** ✅
- `test_validate_foreign_key_to_model_with_overridden_manager (model_forms.tests.ModelFormBasicTests)`: **PASS** ✅

### PASS_TO_PASS regressions
None - all 171 PASS_TO_PASS tests continued to pass.

### Pre-existing failures (not counted, confirmed against base capture)
None - the gate shows OK status with zero failures.

### Resolution summary
The single-line fix changing `_default_manager` to `_base_manager` in ForeignKey.validate() completely resolves the issue:
- Both FAIL_TO_PASS tests now pass
- Zero regressions introduced
- Full contract satisfied: all target tests pass AND no PASS_TO_PASS tests regressed

The diagnosis from recon was accurate and the fix from craft was precise and complete.

VERDICT: RESOLVED
RE-ENTER: none
