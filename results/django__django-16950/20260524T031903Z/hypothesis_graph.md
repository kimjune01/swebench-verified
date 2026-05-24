# Hypothesis graph: django__django-16950

## H₀: Initial symptom observation (abduction)

**Status**: Confirmed by test failure
**Mode**: Abduction

The test `test_inlineformset_factory_nulls_default_pks_alternate_key_relation_data` fails because when an inline formset is created with form data, the parent instance's UUID alternate key field is None when it should contain the default UUID value.

**Evidence**:
- Assertion failure at `tests/model_formsets/test_uuid.py:116`: `self.assertIsNotNone(formset.instance.uuid)` 
- The parent model `ParentWithUUIDAlternateKey` has `uuid = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)`
- The child's ForeignKey uses `to_field="uuid"` to point to this non-primary-key UUID field
- Expected: UUID should be populated with default value
- Actual: UUID is None

## H₁: Root cause identification (deduction)

**Status**: Confirmed by code reading
**Mode**: Deduction (traced code path, found explicit null assignment)
**Confidence**: 95%

The root cause is in `django/forms/models.py` lines 1175-1181 in the `BaseInlineFormSet.add_fields()` method. This code unconditionally sets fields with defaults to None when the parent instance is being added, without distinguishing between primary keys and non-primary-key fields.

**Code path**:
1. `inlineformset_factory()` creates a formset class with `BaseInlineFormSet` as the base
2. `BaseInlineFormSet.__init__()` creates a new parent instance: `self.instance = self.fk.remote_field.model()`
3. During model initialization, the UUID field gets its default value from `uuid.uuid4()`
4. `add_fields()` is called for each form
5. The code detects `to_field="uuid"` and sets `kwargs["to_field"] = "uuid"`
6. **THE BUG**: Lines 1175-1181 check if the instance is being added and if the target field has a default, then sets it to None:

```python
if self.instance._state.adding:
    if kwargs.get("to_field") is not None:
        to_field = self.instance._meta.get_field(kwargs["to_field"])
    else:
        to_field = self.instance._meta.pk
    if to_field.has_default():
        setattr(self.instance, to_field.attname, None)  # Line 1181 - THE BUG
```

**Why this is wrong**:
- For **primary key** fields with defaults (like UUID PKs), setting to None is correct because Django's ORM auto-generates them on save
- For **non-primary-key** fields with defaults (like UUID alternate keys), setting to None is wrong because these fields need their default value immediately for inline formset validation

**Historical context** (from git blame):
- Commit `1306cd1e8a` (#24377): Originally added to fix UUID primary keys
- Commit `a50b66da30` (#24958): Extended to handle `to_field` for alternate keys, but didn't distinguish primary vs non-primary

**Supporting evidence**:
- `django/forms/models.py:1180` - condition checks `to_field.has_default()` but not `to_field.primary_key`
- `django/db/models/fields/__init__.py` - Field class has `primary_key` attribute available for checking
- Passing test `test_inlineformset_factory_ignores_default_pks_on_submit` shows that NULL is correct for primary keys
- Failing test shows that NULL is wrong for alternate keys

## Edit sites

**Primary edit site**:
- `django/forms/models.py` line 1180: Change condition to only null out primary key fields
  - Current: `if to_field.has_default():`
  - Fixed: `if to_field.has_default() and to_field.primary_key:`

This ensures that:
1. Primary key fields with defaults → set to None (regenerated on save)
2. Non-primary-key fields with defaults → keep default value (needed immediately)


---

## Craft Gate Loop

### Iteration 1
**Hypothesis**: Add `and to_field.primary_key` to line 1180 to only null primary key fields with defaults.

**Diff applied**:
```diff
-            if to_field.has_default():
+            if to_field.has_default() and to_field.primary_key:
```

**Gate result**: PARTIAL PASS
- FAIL_TO_PASS test passed ✓
- Regression: `test_inlineformset_factory_nulls_default_pks_alternate_key_relation` failed
- Error: `AssertionError: UUID('...') is not None` - expected None for unbound formset

**Trajectory**: Oscillatory (regression) - fix was too narrow, didn't account for bound vs unbound formsets.

### Iteration 2
**Refinement**: Distinguish between bound (data provided) and unbound (no data) formsets. Non-PK fields should:
- Keep default when formset is bound (data provided) 
- Be set to None when formset is unbound (no data)

**Diff applied**:
```diff
-            if to_field.has_default() and to_field.primary_key:
+            if to_field.has_default() and (to_field.primary_key or not self.is_bound):
```

**Gate result**: PASS ✓
- All 7 tests passed
- FAIL_TO_PASS test: `test_inlineformset_factory_nulls_default_pks_alternate_key_relation_data` ✓
- No regressions

**Resolution**: The fix correctly handles the distinction:
- Primary key fields with defaults: always set to None (auto-generated on save)
- Non-primary key fields with defaults: set to None only when formset is unbound, preserve default when bound


---

## Audit: django__django-16950

**Patch verification against full gate**

### Phase 1: Patch confirmation
```
 django/forms/models.py | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

Patch is live in tree:
```python
-            if to_field.has_default():
+            if to_field.has_default() and (to_field.primary_key or not self.is_bound):
```

### Phase 2: Gate execution
All 7 tests in `model_formsets.test_uuid` passed.

### Phase 3: Result classification

#### FAIL_TO_PASS
- `test_inlineformset_factory_nulls_default_pks_alternate_key_relation_data` ("If form data is provided, a parent's auto-generated alternate key is"): **PASS** ✓

#### PASS_TO_PASS (all passed, no regressions)
- `test_inlineformset_factory_ignores_default_pks_on_submit` ("#24377 - Inlines with a model field default should ignore that default"): **PASS** ✓
- `test_inlineformset_factory_nulls_default_pks` ("#24377 - If we're adding a new object, a parent's auto-generated pk"): **PASS** ✓
- `test_inlineformset_factory_nulls_default_pks_alternate_key_relation` ("#24958 - Variant of test_inlineformset_factory_nulls_default_pks for"): **PASS** ✓
- `test_inlineformset_factory_nulls_default_pks_auto_parent_uuid_child`: **PASS** ✓
- `test_inlineformset_factory_nulls_default_pks_child_editable_pk`: **PASS** ✓
- `test_inlineformset_factory_nulls_default_pks_uuid_parent_auto_child`: **PASS** ✓

#### Pre-existing failures
None.

### Phase 4: Verdict

✓ All FAIL_TO_PASS tests pass
✓ Zero PASS_TO_PASS regressions
✓ Full gate clean

The fix successfully addresses the root cause: primary key fields with defaults are always nulled (auto-generated on save), while non-primary-key fields with defaults (like UUID alternate keys) are only nulled when the formset is unbound. When the formset is bound with data, the default value is preserved for validation.

VERDICT: RESOLVED
RE-ENTER: none
