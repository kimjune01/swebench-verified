# Hypothesis graph: django__django-11951

## H0: Initial diagnosis (abduction → deduction)

**Observation:** Test `test_explicit_batch_size_respects_max_batch_size` fails with `AssertionError: 3 != 4 : 3 queries executed, 4 expected`.

**Test behavior:**
- Creates 1000 Country objects with 3 fields ['name', 'iso_two_letter', 'description']
- Calculates max_batch_size from DB backend: 333 (SQLite limit: 999 params / 3 fields)
- Calls `bulk_create(objs, batch_size=334)` (max_batch_size + 1)
- Expects 4 queries (ceil(1000/333)) but observes 3 queries

**Root cause (deduction - 99% confidence):**
`_batched_insert` at django/db/models/query.py:1212 uses user-provided batch_size without checking if it exceeds the database backend's max_batch_size limit.

Current code:
```python
batch_size = (batch_size or max(ops.bulk_batch_size(fields, objs), 1))
```

This OR logic means: "use batch_size if provided, otherwise calculate max". It does NOT enforce the maximum when batch_size is explicitly provided.

**Supporting evidence:**
- django/db/models/query.py:1212 - buggy OR logic
- django/db/models/query.py:523 - bulk_update uses correct pattern: `batch_size = min(batch_size, max_batch_size) if batch_size else max_batch_size`
- git blame shows bulk_create logic from 2012, bulk_update from 2018 with correct min() pattern
- Problem statement explicitly mentions bulk_update has the right logic

**Edit site:**
- django/db/models/query.py:1212 in `_batched_insert` method

**Fix specification:**
Replace single line 1212 with two lines matching bulk_update pattern:
```python
max_batch_size = max(ops.bulk_batch_size(fields, objs), 1)
batch_size = min(batch_size, max_batch_size) if batch_size else max_batch_size
```

**Confidence:** Deduction - 99%
Direct code trace + comparison with working bulk_update + git history confirms this is the bug.

## Gate iteration 1: Fix applied, green gate

**Action:** Applied fix to django/db/models/query.py:1212-1213
```python
-        batch_size = (batch_size or max(ops.bulk_batch_size(fields, objs), 1))
+        max_batch_size = max(ops.bulk_batch_size(fields, objs), 1)
+        batch_size = min(batch_size, max_batch_size) if batch_size else max_batch_size
```

**Gate result:** ✅ GREEN
- test_explicit_batch_size_respects_max_batch_size: PASS
- All 27 tests passed (5 skipped)
- No regressions

**E-value trajectory:** Convergent (immediate resolution)

**Resolution:** RESOLVED - FAIL_TO_PASS test now passes, no PASS_TO_PASS regressions.

---

# Audit: django__django-11951

## FAIL_TO_PASS
- `test_explicit_batch_size_respects_max_batch_size`: **PASS** ✅

## PASS_TO_PASS regressions
None. All 22 PASS_TO_PASS tests remain passing:
- test_batch_same_vals: ok
- test_bulk_insert_expressions: ok
- test_bulk_insert_nullable_fields: ok
- test_efficiency: ok
- test_empty_model: ok
- test_explicit_batch_size: ok
- test_explicit_batch_size_efficiency: ok
- test_ignore_conflicts_ignore: ok
- test_large_batch: ok
- test_large_batch_efficiency: ok
- test_large_batch_mixed: ok
- test_large_batch_mixed_efficiency: ok
- test_large_single_field_batch: ok
- test_long_and_short_text: ok
- test_long_non_ascii_text: ok
- test_multi_table_inheritance_unsupported: ok
- test_non_auto_increment_pk: ok
- test_non_auto_increment_pk_efficiency: ok
- test_proxy_inheritance_supported: ok
- test_set_state_with_pk_specified: ok
- test_simple: ok
- (Additional skipped tests not counted)

## Pre-existing failures
None (confirmed against base capture).

## Patch applied
```diff
diff --git a/django/db/models/query.py b/django/db/models/query.py
index 794e0faae7..92349cd0c5 100644
--- a/django/db/models/query.py
+++ b/django/db/models/query.py
@@ -1209,7 +1209,8 @@ class QuerySet:
         if ignore_conflicts and not connections[self.db].features.supports_ignore_conflicts:
             raise NotSupportedError('This database backend does not support ignoring conflicts.')
         ops = connections[self.db].ops
-        batch_size = (batch_size or max(ops.bulk_batch_size(fields, objs), 1))
+        max_batch_size = max(ops.bulk_batch_size(fields, objs), 1)
+        batch_size = min(batch_size, max_batch_size) if batch_size else max_batch_size
         inserted_rows = []
         bulk_return = connections[self.db].features.can_return_rows_from_bulk_insert
         for item in [objs[i:i + batch_size] for i in range(0, len(objs), batch_size)]:
```

## Summary
The fix correctly enforces the database backend's max_batch_size limit by:
1. Computing max_batch_size from the backend's bulk_batch_size
2. Using min(batch_size, max_batch_size) when batch_size is explicitly provided
3. Matching the pattern already used successfully in bulk_update

Full gate: 27 tests ran, all passed (5 skipped). Zero regressions.

VERDICT: RESOLVED
RE-ENTER: none
