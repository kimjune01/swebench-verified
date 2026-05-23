# Hypothesis graph: django__django-16661

## H₀: Initial symptom (abduction)
**Node**: symptom
**Type**: abduction
**Confidence**: 99%

The test `test_lookup_allowed_foreign_primary` fails with `AssertionError: False is not True`. The call `ma.lookup_allowed("restaurant__place__country", "1")` returns `False` when it should return `True`, despite `"restaurant__place__country"` being in the `list_filter`.

## H₁: Root cause - incorrect parent_link assumption (deduction)
**Node**: root-cause
**Type**: deduction
**Confidence**: 98%

In `django/contrib/admin/options.py:467-472`, the `lookup_allowed` method builds `relation_parts` by walking the lookup chain. The condition:
```python
if not prev_field or (
    prev_field.is_relation
    and field not in prev_field.path_infos[-1].target_fields
):
    relation_parts.append(part)
```

This skips adding a field to `relation_parts` when it's in the `target_fields` of the previous relation. This optimization is intended for concrete model inheritance where the parent's primary key is accessible via `parent_ptr`.

**The bug**: When a `OneToOneField` has `primary_key=True` (like `Restaurant.place`), it becomes the target field of any FK pointing to that model. The code incorrectly treats this the same as a `parent_link=True` field (concrete inheritance) and skips it, even though it's a distinct relationship that must be traversed.

**Evidence from container**:
- `Restaurant.place.remote_field.parent_link = False` (explicit OneToOne, not inheritance)
- `Restaurant.place in waiter.restaurant.path_infos[-1].target_fields = True` (it's the PK)
- Result: `"place"` is skipped from `relation_parts`, producing `["restaurant", "country"]` instead of `["restaurant", "place", "country"]`
- The final check compares `"restaurant__country"` against `list_filter` which contains `"restaurant__place__country"`, causing the False return

## Edit sites

**File**: `django/contrib/admin/options.py`
**Lines**: 467-472

**Change**: Modify the condition to only skip fields that are both in `target_fields` AND have `parent_link=True`. A OneToOneField with `primary_key=True` but `parent_link=False` should still be included in `relation_parts`.

The condition should become:
```python
if not prev_field or (
    prev_field.is_relation
    and (
        field not in prev_field.path_infos[-1].target_fields
        or not getattr(field.remote_field, 'parent_link', False)
    )
):
    relation_parts.append(part)
```

This ensures:
- Regular fields not in target_fields: added ✓
- OneToOneField with primary_key=True, parent_link=False: added ✓
- OneToOneField with parent_link=True (concrete inheritance): skipped ✓

## Craft Phase - Gate Loop

### Iteration 1: Initial Fix (FAILED - codex review)
**Approach**: Add `parent_link` check to `prev_field.remote_field.parent_link`
**codex Feedback**: Checking wrong field - should check the field being skipped (`field`), not `prev_field`. Would break normal FK target field lookups like `country__id`.
**Status**: Rejected before gate, revised

### Iteration 2: Revised Fix (FAILED - codex review)  
**Approach**: Check `field.remote_field.parent_link` instead
**codex Feedback**: Still too broad - normal non-relational target fields like `Employee.id` don't have `remote_field`, this would stop skipping them and break existing behavior.
**Status**: Rejected before gate, revised

### Iteration 3: Final Fix (PASSED)
**Approach**: Skip target fields UNLESS they are relational fields (`field.is_relation`) that aren't `parent_link` fields.

**Implementation** (django/contrib/admin/options.py:467-476):
```python
if not prev_field or (
    prev_field.is_relation
    and (
        field not in prev_field.path_infos[-1].target_fields
        or (
            field.is_relation
            and not getattr(field.remote_field, "parent_link", False)
        )
    )
):
    relation_parts.append(part)
```

**Logic**:
- Non-relational target fields (like `id`): Still skipped - preserves existing behavior
- Relational target fields with `parent_link=True`: Skipped - preserves inheritance optimization  
- Relational target fields with `parent_link=False` (like `OneToOneField(primary_key=True)`): NOT skipped - fixes the bug

**Gate Result**: ✅ ALL PASS (37 tests, 0 failures)
- `test_lookup_allowed_foreign_primary`: ✅ PASS
- All existing tests: ✅ PASS

**Trajectory**: Convergent - fix addresses root cause identified in recon

**Resolution**: RESOLVED - FAIL_TO_PASS test passes, no regressions

---

# Audit: django__django-16661

## FAIL_TO_PASS
- test_lookup_allowed_foreign_primary (modeladmin.tests.ModelAdminTests.test_lookup_allowed_foreign_primary): **PASS** ✓

## PASS_TO_PASS regressions
**None** — all 37 tests passed

## Pre-existing (not counted, confirmed against base capture)
**None** — no failures in base or patched run

## Summary
The craft patch successfully resolves the issue:
- ✅ FAIL_TO_PASS test now passes
- ✅ Zero regressions introduced
- ✅ All 37 tests in the suite pass

The fix correctly distinguishes between:
1. Parent-link fields (concrete inheritance) — properly skipped
2. OneToOneField with `primary_key=True` but `parent_link=False` — now properly traversed
3. Non-relational target fields like `id` — still skipped as before

VERDICT: RESOLVED
RE-ENTER: none
