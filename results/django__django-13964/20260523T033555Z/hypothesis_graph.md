# Hypothesis Graph: django__django-13964

## H₀: Initial Observation (Abduction)
The test fails with `ParentStringPrimaryKey.DoesNotExist` and an `IntegrityError` showing that `child.parent_id` contains empty string '' instead of 'jeff'.

## H₁: Root Cause (Deduction - 95%)

**Location**: `django/db/models/base.py`, lines 911-943, specifically line 937

**The Bug**:
The `_prepare_related_fields_for_save()` method only updates the FK field from the cached parent object when the FK field is `None`:

```python
elif getattr(self, field.attname) is None:
    setattr(self, field.attname, obj.pk)
```

**Why This Fails for CharField PKs**:
1. When `parent = ParentStringPrimaryKey()` is created, `parent.name` (a CharField PK) initializes to empty string ''
2. When `child.parent = parent` is executed, the `ForwardManyToOneDescriptor.__set__` (line 248-249 of related_descriptors.py) copies parent.name to child.parent_id:
   ```python
   setattr(child, 'parent_id', getattr(parent, 'name'))  # Sets child.parent_id = ''
   ```
3. When `child.parent.name = 'jeff'` is set, only the cached parent object is updated
4. When `child.save()` is called, line 937 checks `child.parent_id is None`, which is False (it's '')
5. So the FK field doesn't get updated
6. Line 941-943 detects the mismatch ('jeff' != '') but only clears the cache, doesn't update the FK field

**Why This Works for AutoField PKs**:
For AutoField PKs, the initial value is `None`, not '', so line 937's check passes and the FK field gets updated.

**Supporting Evidence**:
- `django/db/models/base.py:937` - Only checks `is None`
- `django/db/models/base.py:941-943` - Detects mismatch but only clears cache
- `django/db/models/fields/related_descriptors.py:248-249` - Copies PK value at assignment time
- Git commit 519016e5f2 (2019) added the `is None` check to fix issue #28147 for AutoField PKs

## Edit Sites

**Primary Fix** (`django/db/models/base.py:937-939`):
Change the condition to handle not just `None` but also empty string or any "uninitialized" FK value. The safest approach is to check if the FK field doesn't match the cached object's PK AND the FK field appears uninitialized:

```python
fk_value = getattr(self, field.attname)
pk_value = getattr(obj, field.target_field.attname)
if fk_value != pk_value and (fk_value is None or fk_value == ''):
    setattr(self, field.attname, obj.pk)
```

**Alternative** (simpler but must verify it doesn't break test_cached_relation_invalidated_on_save):
Replace `is None` with `!= getattr(obj, field.target_field.attname)` to update whenever there's a mismatch.

## Open Questions
1. Should we check for `` specifically, or use a more general "empty" check?
2. Does this interact correctly with `test_cached_relation_invalidated_on_save` which expects cache clearing when FK is changed directly?
3. Are there other field types besides CharField that have non-None initial values?

## Craft Gate Loop

### Iteration 1: Initial Fix

**Hypothesis**: Line 936 in `django/db/models/base.py` only checks `is None`, but CharField PKs default to `''`. Need to check if FK value is in `field.target_field.empty_values` to handle both `None` and `''`.

**Edit Applied**:
```diff
--- a/django/db/models/base.py
+++ b/django/db/models/base.py
@@ -933,7 +933,7 @@ class Model(metaclass=ModelBase):
                         "related object '%s'." % (operation_name, field.name)
                     )
-                elif getattr(self, field.attname) is None:
+                elif getattr(self, field.attname) in field.target_field.empty_values:
                     # Use pk from related object if it has been saved after
                     # an assignment.
                     setattr(self, field.attname, obj.pk)
```

**Codex Review**: Approved. The change is minimal, semantically correct (uses target field's empty_values), and preserves existing cache-clearing logic. Notes that the fix is broader than just CharField (handles all empty values) but this is acceptable since `''` is already an empty value in Django.

**Gate Result**: ✅ PASS
- All 37 tests in many_to_one.tests.ManyToOneTests pass
- `test_save_fk_after_parent_with_non_numeric_pk_set_on_child` now passes
- No regressions, including `test_cached_relation_invalidated_on_save` which was a concern

**Trajectory**: Convergent (successful) — single iteration to resolution.

**Root Cause Confirmed**: The recon diagnosis was correct. CharField PKs initialize to `''`, not `None`, so the `is None` check failed to update FK fields when a cached parent's PK was modified after FK assignment. Using `in field.target_field.empty_values` handles both `None` and `''` using Django's canonical empty-value semantics.

---

# Audit: django__django-13964

## FAIL_TO_PASS
- `test_save_fk_after_parent_with_non_numeric_pk_set_on_child`: **PASS** ✅

## PASS_TO_PASS regressions
None — all 37 tests passed.

## Pre-existing failures (not counted)
None identified.

## Classification

The patch successfully fixes the issue by changing the condition from `getattr(self, field.attname) is None` to `getattr(self, field.attname) in field.target_field.empty_values`. This handles both `None` (for AutoField) and `''` (for CharField) using Django's canonical empty-value semantics.

**Gate output**: All 37 tests in `many_to_one.tests.ManyToOneTests` pass, including:
- The target FAIL_TO_PASS test now passes
- All PASS_TO_PASS tests continue to pass
- No regressions introduced

The fix is minimal (1 line), semantically correct, and preserves all existing behavior while extending support to non-numeric primary keys.
