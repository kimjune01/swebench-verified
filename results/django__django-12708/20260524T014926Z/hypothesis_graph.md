# Hypothesis graph: django__django-12708

## H₀ [abduction, 95%]
**Root cause**: `alter_index_together` deletion filters by `index=True` but doesn't exclude `unique=True`, so it finds both the index_together index AND the unique_together constraint when they're on the same fields.

**Evidence**:
- `django/db/backends/base/schema.py:396` - Calls `_delete_composed_index(model, fields, {'index': True}, ...)` with only `index=True` filter
- `django/db/backends/base/schema.py:380` - Comparison: `alter_unique_together` correctly uses `{'unique': True}` filter
- `django/db/backends/base/introspection.py:166-183` - Documentation: unique constraints have BOTH `unique=True` AND `index=True` (unique constraints are implemented as unique indexes)
- `django/db/backends/base/schema.py:1159` - `_constraint_names` filters by `index` parameter: `if index is not None and infodict['index'] != index`
- `tests/migrations/test_base.py` - Test helper `assertIndexExists` explicitly checks `not c['unique']` to distinguish regular indexes from unique constraints
- Stack trace: ValueError at line 414 shows 2 constraints found when expecting 1

**Edit site**:
- `django/db/backends/base/schema.py:396` - Change `{'index': True}` to `{'index': True, 'unique': False}` to filter out unique constraints when deleting index_together

**Competing hypotheses**: None - code path is deterministic and evidence is deductive.

**Rejected hypotheses**: None yet.


## Craft: Gate Loop

### Iteration 1: Applied fix, green gate

**Action**: Changed `django/db/backends/base/schema.py:396` from `{'index': True}` to `{'index': True, 'unique': False}` in `alter_index_together` method.

**Codex volley**: "No blocking issue in the code change. `{"index": True, "unique": False}` is the right filter. `_constraint_names()` treats `unique=False` as an exact match, so the unique constraint is no longer included while the regular `index_together` index still is."

**Gate result**: ✅ PASS
```
test_alter_index_together_remove_with_unique_together (migrations.test_operations.OperationTests) ... ok

----------------------------------------------------------------------
Ran 1 test in 0.016s

OK
```

**Status**: RESOLVED — FAIL_TO_PASS test passes on first gate iteration.

## Audit: django__django-12708

### Patch verification
```diff
diff --git a/django/db/backends/base/schema.py b/django/db/backends/base/schema.py
index 61f88401ab..1f521cfc5c 100644
--- a/django/db/backends/base/schema.py
+++ b/django/db/backends/base/schema.py
@@ -393,7 +393,7 @@ class BaseDatabaseSchemaEditor:
         news = {tuple(fields) for fields in new_index_together}
         # Deleted indexes
         for fields in olds.difference(news):
-            self._delete_composed_index(model, fields, {'index': True}, self.sql_delete_index)
+            self._delete_composed_index(model, fields, {'index': True, 'unique': False}, self.sql_delete_index)
         # Created indexes
         for field_names in news.difference(olds):
             fields = [model._meta.get_field(field) for field in field_names]
```

### Gate results (102 tests)
All tests passed, including the three alter_index_together tests:
- `test_alter_index_together` ... ok
- `test_alter_index_together_remove` ... ok  
- `test_alter_index_together_remove_with_unique_together` ... ok ✅ (FAIL_TO_PASS)

Full suite: 102 tests in 0.673s - OK

## FAIL_TO_PASS
- test_alter_index_together_remove_with_unique_together: **PASS** ✅

## PASS_TO_PASS regressions
**None** — all 102 tests passed with no failures.

## Pre-existing failures (not counted)
**None** — baseline capture showed tests passing, current run shows all tests passing.

## Kill report
Not applicable — patch is RESOLVED.

The fix correctly adds `'unique': False` to filter out unique constraints when deleting index_together indexes, preventing the ValueError when both index_together and unique_together exist on the same fields.

