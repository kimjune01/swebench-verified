# Hypothesis graph: django__django-11087

## Hypothesis H1 (initial diagnosis)

**Type:** Abduction  
**Confidence:** 85%

**Failure mode:** The test `test_only_referenced_fields_selected` expects that when deleting an `Origin` object that cascades to `Referrer` objects, the SELECT query for `Referrer` should only include fields that are actually referenced by other models (`id` and `unique_field`), not all fields (`id`, `origin_id`, `unique_field`, `large_field`).

**Root cause:** The `Collector.related_objects()` method in `django/db/models/deletion.py` (lines 232-236) builds a QuerySet for related objects without specifying which fields to select. Django's ORM defaults to selecting all fields when no `.only()` or `.defer()` is used.

**Evidence:**
- `django/db/models/deletion.py:232-236` - The `related_objects()` method returns a filtered QuerySet without field selection
- Test failure shows SQL includes `origin_id` and `large_field` when only `id` and `unique_field` are needed
- `SecondReferrer.referrer` references `Referrer.id` (implicit pk)
- `SecondReferrer.other_referrer` references `Referrer.unique_field` (via `to_field`)

**Required changes:**
1. Modify `related_objects()` to determine which fields are referenced by foreign keys from other models
2. Use `.only()` to select only referenced fields plus the primary key
3. Check for deletion signals - if connected, select all fields (signal handlers need full instances)

**Implementation approach:**
- Call `get_candidate_relations_to_delete()` on the related model to find all reverse foreign key relations
- For each relation, get `relation.field.target_field.name` to find which field is referenced
- Collect all referenced field names in a set, add the pk field name
- Check `signals.pre_delete.has_listeners()` and `signals.post_delete.has_listeners()`
- If signals are connected, return the full QuerySet; otherwise apply `.only()`


## Gate Loop - Iteration 1

**Approach:** Modified `Collector.related_objects()` to apply `.only()` with referenced fields when no deletion signals are connected.

**Changes:**
- `django/db/models/deletion.py:231-253` - Updated `related_objects()` method to:
  1. Check if deletion signals (`pre_delete` or `post_delete`) are connected to the model
  2. If signals are connected, return full queryset (all fields needed for signal handlers)
  3. Otherwise, collect fields referenced by foreign keys from other models using `get_candidate_relations_to_delete()`
  4. Use `relation.field.foreign_related_fields` to support multi-column foreign keys
  5. Always include the primary key field
  6. Apply `.only(*referenced_fields)` to the queryset

**Codex Feedback (pre-gate):**
- Critical catch: Initially used `relation.field.target_field.name` which only handles single-column ForeignKey
- Revised to use `relation.field.foreign_related_fields` to support ForeignObject with multiple target fields
- This ensures compatibility with Django's full relation API

**Gate Result:** ✅ PASS
- All 43 tests passed including `test_only_referenced_fields_selected`
- The fix correctly selects only `id` and `unique_field` for Referrer during cascade deletion from Origin
- Signal behavior verified: when signals are connected, all fields including `large_field` are selected

**Status:** RESOLVED - FAIL_TO_PASS test now passes

---

# Audit: django__django-11087

## FAIL_TO_PASS
- test_only_referenced_fields_selected (delete.tests.DeletionTests): **PASS** ✓

## PASS_TO_PASS regressions
none

## Pre-existing (not counted, confirmed against base capture)
none

## Summary
The patch successfully fixes the failing test. The deletion collector now correctly identifies only-fields when building the dependency graph, ensuring only referenced fields are selected in the deletion query. All 42 tests pass with 1 expected skip.

VERDICT: RESOLVED
RE-ENTER: none
