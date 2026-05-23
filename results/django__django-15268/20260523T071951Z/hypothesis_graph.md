# Hypothesis graph: django__django-15268

## H0: Baseline observation (abduction)
**Timestamp**: 2026-05-22 (recon phase 1)
**Status**: Confirmed

The tests fail because the optimizer is generating 4 AlterFooTogether operations instead of 2:
- AlterUniqueTogether(name='book', unique_together=set())
- AlterIndexTogether(name='book', index_together=set())
- AlterUniqueTogether(name='book', unique_together={('title', 'author')})
- AlterIndexTogether(name='book', index_together={('title', 'author')})

Expected: just operations 3 and 4 (without the clearing operations 1 and 2).

**Evidence**:
- Test output shows all 4 operations present
- Tests expect only 2 operations

## H1: Root cause - AlterFooTogether operations cannot reduce across each other (deduction)
**Timestamp**: 2026-05-22 (recon phase 3)
**Status**: High confidence - deduction from code trace

The optimizer cannot reduce operation pairs (1→3, 2→4) because AlterUniqueTogether and AlterIndexTogether cannot optimize ACROSS each other. The optimizer's left-reduction logic requires all in-between operations to return `True` when asked to reduce across the target operation, but ModelOptionOperation.reduce() returns `False` for different operation classes.

**Code path**:
1. Autodetector generates 4 operations via `_generate_removed_altered_foo_together` (lines 1171-1184) and `_generate_altered_foo_together` (lines 1193-1207)
2. Optimizer calls AlterUniqueTogether(set()).reduce(AlterUniqueTogether({...})) with AlterIndexTogether in between
3. For left reduction, checks: AlterIndexTogether(set()).reduce(AlterUniqueTogether({...}))
4. ModelOptionOperation.reduce() (line 411-413) doesn't match (different classes) → calls super()
5. ModelOperation.reduce() (line 34-37) returns `False` because operation references same model
6. Left reduction fails, operations not optimized

**Supporting evidence**:
- `django/db/migrations/operations/models.py:411-413`: ModelOptionOperation.reduce() only handles same-class reductions
- `django/db/migrations/optimizer.py:53-58`: Left reduction requires `all(op.reduce(other, app_label) is True for op in in_between)`
- AlterUniqueTogether and AlterIndexTogether are independent operations (affect different constraints) and should be reorderable

**Confidence**: 95% (deduction)


## Edit sites enumeration
**Timestamp**: 2026-05-22 (recon phase 4)

Primary edit site:
- `django/db/migrations/operations/models.py:470-529` (AlterTogetherOptionOperation class)
  - Add or override `reduce` method to handle cross-class optimization between AlterUniqueTogether and AlterIndexTogether

Secondary verification:
- Optimizer algorithm in `django/db/migrations/optimizer.py:40-69` is correct as-is
- No changes needed to autodetector - it correctly generates the operations


## Craft: Gate Loop

### Iteration 1 (codex pre-gate volley)

**Draft diff:**
```diff
--- a/django/db/migrations/operations/models.py
+++ b/django/db/migrations/operations/models.py
@@ -478,6 +478,17 @@ class AlterTogetherOptionOperation(ModelOptionOperation):
     def __init__(self, name, option_value):
         if option_value:
             option_value = set(normalize_together(option_value))
         setattr(self, self.option_name, option_value)
         super().__init__(name)
+
+    def reduce(self, operation, app_label):
+        # Same class reduction (existing behavior from parent)
+        if isinstance(operation, (self.__class__, DeleteModel)) and self.name_lower == operation.name_lower:
+            return [operation]
+        # Cross-class optimization for AlterTogetherOptionOperation subclasses
+        elif isinstance(operation, AlterTogetherOptionOperation) and self.name_lower == operation.name_lower:
+            return True  # Can optimize across
+        return super().reduce(operation, app_label)
```

**codex feedback:**
- Comment misleading (duplicates parent logic rather than preserving it)
- Better to delegate to super() first
- Should explicitly check `self.option_name != operation.option_name`
- Suggested cleaner implementation calling super() first

**Revised diff (applied):**
```diff
--- a/django/db/migrations/operations/models.py
+++ b/django/db/migrations/operations/models.py
@@ -478,6 +478,18 @@ class AlterTogetherOptionOperation(ModelOptionOperation):
     def __init__(self, name, option_value):
         if option_value:
             option_value = set(normalize_together(option_value))
         setattr(self, self.option_name, option_value)
         super().__init__(name)
+
+    def reduce(self, operation, app_label):
+        result = super().reduce(operation, app_label)
+        if result is not False:
+            return result
+        if (
+            isinstance(operation, AlterTogetherOptionOperation) and
+            self.name_lower == operation.name_lower and
+            self.option_name != operation.option_name
+        ):
+            return True
+        return False
```

**Gate outcome:** GREEN ✓

All 140 tests passed, including all three FAIL_TO_PASS:
- test_foo_together_ordering: "index/unique_together also triggers on ordering changes."
- test_remove_field_and_foo_together: "Removed fields will be removed after updating index/unique_together."
- test_rename_field_and_foo_together: "Fields are renamed before updating index/unique_together."

**Trajectory:** Convergent-success (first attempt)

**Root cause confirmed:** The migration optimizer's left-reduction algorithm was blocked because AlterUniqueTogether and AlterIndexTogether couldn't optimize across each other. Adding a `reduce()` method override in `AlterTogetherOptionOperation` that returns `True` for cross-class optimization (when operating on the same model but different options) enables the optimizer to reduce redundant clear-then-set operation pairs.

**Resolution:** Single minimal edit to `django/db/migrations/operations/models.py`, adding the `reduce()` method to enable cross-option optimization for AlterTogetherOptionOperation subclasses.


## Audit: django__django-15268
**Timestamp**: 2026-05-22
**Status**: RESOLVED

### FAIL_TO_PASS (all passing ✓)
- test_remove_field_and_foo_together: PASS
- test_rename_field_and_foo_together: PASS  
- test_order_fields_indexes: PASS

### PASS_TO_PASS regressions
None — all 140 tests passed.

### Pre-existing failures
None.

### Full gate results
```
Ran 140 tests in 0.066s
OK
```

**Verification:**
- Patch is live: `django/db/migrations/operations/models.py | 13 +++++++++++++`
- All FAIL_TO_PASS tests now passing
- Zero PASS_TO_PASS regressions introduced
- Full contract satisfied
