# Hypothesis graph: django__django-14559

## H₀ (Abduction)
The tests fail because `bulk_update()` returns `None` instead of returning the number of rows updated.

### Evidence
- Test output shows: `AssertionError: None != 0`, `AssertionError: None != 2000`, `AssertionError: None != 1`
- All three tests expect `bulk_update()` to return an integer row count
- Currently, `bulk_update()` has no explicit return statement (returns `None` implicitly)

**File**: `django/db/models/query.py:527-566`
**Mode**: Abduction
**Confidence**: 95% (deduction from code inspection)

## H₁ (Root Cause - Deduction)
The `bulk_update()` method has two defects preventing it from returning row counts:

1. **Line 544**: Early return for empty objects list returns `None` instead of `0`
   ```python
   if not objs:
       return  # Returns None, should return 0
   ```

2. **Lines 565-566**: Calls `update()` in a loop but doesn't capture or accumulate return values
   ```python
   for pks, update_kwargs in updates:
       self.filter(pk__in=pks).update(**update_kwargs)  # Return value discarded
   ```

### Supporting Evidence
- `django/db/models/query.py:785` - The `update()` method returns `rows` (the number of rows updated)
- `django/db/models/query.py:788` - Confirmed: `return rows`
- The problem statement explicitly says `update()` returns row count and `bulk_update()` should accumulate these
- Inspected `django/db/models/base.py:2138` - existing caller doesn't rely on None return value, so change is backward compatible

**Mode**: Deduction
**Confidence**: 99% (traced code paths and confirmed behavior matches test expectations)

## Edit Sites

1. **django/db/models/query.py:544**
   - Change: `return` → `return 0`
   - Reason: Return 0 when no objects to update

2. **django/db/models/query.py:563-566** (the transaction block)
   - Add before the `for` loop: `rows_updated = 0`
   - Change the update call to: `rows_updated += self.filter(pk__in=pks).update(**update_kwargs)`
   - Add after the transaction block: `return rows_updated`
   - Reason: Accumulate row counts from each batch and return the total

## Competing Hypotheses
None - the root cause is clear from code inspection.

## Rejected Hypotheses
None - first diagnosis pass.

## Open Questions
None - the fix is straightforward.

## Craft Gate Loop

### Iteration 1: Initial fix applied

**Changes:**
1. Line 544: Changed `return` to `return 0` for empty objects case
2. Added `rows_updated = 0` initialization inside transaction block
3. Changed `self.filter(pk__in=pks).update(**update_kwargs)` to `rows_updated += self.filter(pk__in=pks).update(**update_kwargs)`
4. Added `return rows_updated` after transaction block

**codex review (pre-gate):** Approved implementation as functionally correct. Noted that:
- Core change is correct
- Duplicate PKs across batches will be counted per batch (intentional behavior)
- No breakage to existing callers

**Gate result:** ✅ PASS
- test_empty_objects: PASS
- test_large_batch: PASS  
- test_updated_rows_when_passing_duplicates: PASS
- All 26 tests in test_bulk_update.py: PASS

**Resolution:** FAIL_TO_PASS tests satisfied on first gate run.

---

# Audit: django__django-14559

## Patch Verification

Patch is live in the tree:
```
 django/db/models/query.py | 6 ++++--
 1 file changed, 4 insertions(+), 2 deletions(-)
```

## FAIL_TO_PASS Results

All three FAIL_TO_PASS tests now **PASS**:

- ✅ test_empty_objects (queries.test_bulk_update.BulkUpdateTests) — PASS
- ✅ test_large_batch (queries.test_bulk_update.BulkUpdateTests) — PASS  
- ✅ test_updated_rows_when_passing_duplicates (queries.test_bulk_update.BulkUpdateTests) — PASS

## PASS_TO_PASS Regressions

**None.** All 26 tests in the gate output passed, including all PASS_TO_PASS tests:
- test_batch_size (queries.test_bulk_update.BulkUpdateNoteTests) — ok
- test_foreign_keys_do_not_lookup (queries.test_bulk_update.BulkUpdateNoteTests) — ok
- test_functions (queries.test_bulk_update.BulkUpdateNoteTests) — ok
- test_multiple_fields (queries.test_bulk_update.BulkUpdateNoteTests) — ok
- test_set_field_to_null (queries.test_bulk_update.BulkUpdateNoteTests) — ok
- test_set_mixed_fields_to_null (queries.test_bulk_update.BulkUpdateNoteTests) — ok
- test_simple (queries.test_bulk_update.BulkUpdateNoteTests) — ok
- test_unsaved_models (queries.test_bulk_update.BulkUpdateNoteTests) — ok
- test_booleanfield (queries.test_bulk_update.BulkUpdateTests) — ok
- test_custom_db_columns (queries.test_bulk_update.BulkUpdateTests) — ok
- test_custom_pk (queries.test_bulk_update.BulkUpdateTests) — ok
- test_datetime_field (queries.test_bulk_update.BulkUpdateTests) — ok
- test_falsey_pk_value (queries.test_bulk_update.BulkUpdateTests) — ok
- test_field_references (queries.test_bulk_update.BulkUpdateTests) — ok
- test_inherited_fields (queries.test_bulk_update.BulkUpdateTests) — ok
- test_invalid_batch_size (queries.test_bulk_update.BulkUpdateTests) — ok
- test_ipaddressfield (queries.test_bulk_update.BulkUpdateTests) — ok
- test_json_field (queries.test_bulk_update.BulkUpdateTests) — ok
- test_no_fields (queries.test_bulk_update.BulkUpdateTests) — ok
- test_nonexistent_field (queries.test_bulk_update.BulkUpdateTests) — ok
- test_only_concrete_fields_allowed (queries.test_bulk_update.BulkUpdateTests) — ok
- test_update_custom_primary_key (queries.test_bulk_update.BulkUpdateTests) — ok
- test_update_primary_key (queries.test_bulk_update.BulkUpdateTests) — ok

## Pre-existing Failures

**None.** The fail-on-base capture showed all tests passing on the unpatched base.

## Gate Output

```
Ran 26 tests in 0.211s

OK
```

## Verdict Rationale

✅ All 3 FAIL_TO_PASS tests now pass  
✅ Zero PASS_TO_PASS regressions  
✅ Complete contract satisfied

The fix correctly:
1. Returns `0` when `objs` is empty (early-return case)
2. Accumulates row counts across batches using `rows_updated += ...`
3. Returns the total `rows_updated` at the end

VERDICT: RESOLVED
RE-ENTER: none
