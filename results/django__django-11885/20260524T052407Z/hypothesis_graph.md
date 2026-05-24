# Hypothesis graph: django__django-11885

## Hypothesis H0 (abduction)
**When**: 2026-05-23
**Claim**: The test fails because `Collector.delete()` executes each queryset in `self.fast_deletes` separately (lines 313-315 of deletion.py), creating multiple DELETE queries to the same table instead of combining them with OR.

**Evidence**:
- Test expects 2 queries but gets 3:
  1. `DELETE FROM "delete_secondreferrer" WHERE "delete_secondreferrer"."referrer_id" IN (1)`
  2. `DELETE FROM "delete_secondreferrer" WHERE "delete_secondreferrer"."other_referrer_id" IN (42)`
  3. `DELETE FROM "delete_referrer" WHERE "delete_referrer"."id" IN (1)`
- Queries 1 and 2 target the same table but use different WHERE clauses
- `SecondReferrer` model has two FKs to `Referrer`: `referrer` (to id) and `other_referrer` (to unique_field)

**Root cause**: Each FK creates a separate queryset entry in `self.fast_deletes` at line 228 via `related_objects()`, and the delete loop (lines 313-315) executes them independently.

**Proposed fix**: Group querysets by model before execution and combine same-model querysets using the `|` operator (which uses `query.combine(other.query, sql.OR)` internally).

**Confidence**: Deduction — 95%
**Supporting code**:
- `django/db/models/deletion.py:313-315` — loop executes each qs separately
- `django/db/models/deletion.py:228` — each FK appends to fast_deletes
- `django/db/models/deletion.py:252-258` — related_objects creates filtered queryset
- `django/db/models/query.py:324-335` — QuerySet.__or__ supports combining

## Craft gate loop

### Iteration 1: Initial fix (too broad)
**Approach**: Group fast_deletes by model only, combine all querysets for same model with OR
**Diff**: Added `defaultdict` grouping by `qs.model`, combined all querysets per model
**Result**: DIVERGENT - FAIL_TO_PASS passed but 2 tests regressed (test_large_delete, test_large_delete_related)
**Evidence**: Expected 25/23 queries, got 22/21 - combining across batches violated SQL parameter limit boundaries

**codex feedback**: Models aren't orderable in Python 3 (TypeError risk from sorting), but main issue is combining across batches that were intentionally split for SQL parameter limits. Need to group by `(model, batch_key)` not just `model`.

### Iteration 2: Batch-aware grouping
**Approach**: Modified `fast_deletes` to store `(batch_key, queryset)` tuples; group by `(model, batch_key)` in execution
**Changes**:
1. Line 194: Added `batch_key = id(objs)` before `append((batch_key, objs))`
2. Line 229: Added `batch_key = tuple(obj.pk for obj in batch)` before `append((batch_key, sub_objs))`
3. Execution loop: Changed to `for batch_key, qs in self.fast_deletes` and group by `(model, batch_key)`

**Result**: CONVERGENT - All 45 tests pass (1 skipped)
**Status**: ✅ RESOLVED

**Final fix**: Combines querysets only when they're for the same model AND same batch of parent objects, preserving intentional batching while eliminating redundant queries for multiple FK paths.

## Audit (2026-05-23)

### FAIL_TO_PASS
- test_fast_delete_combined_relationships: **PASS** ✓

### PASS_TO_PASS regressions
None

### Pre-existing failures (not counted)
None

### Gate result
Ran 45 tests in 0.657s - OK (skipped=1)

VERDICT: RESOLVED
RE-ENTER: none
