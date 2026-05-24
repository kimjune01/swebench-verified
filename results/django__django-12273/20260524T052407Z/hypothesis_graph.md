# Hypothesis graph: django__django-12273

## H₀ (abduction, 2026-05-23)
The tests fail because Django doesn't sync parent pointer fields to parent pk fields when creating new child instances by setting pk=None.

### Evidence
- `test_create_new_instance_with_pk_equals_none`: IntegrityError at `p2.save()` - UNIQUE constraint failed on `user_ptr_id`
- `test_create_new_instance_with_pk_equals_none_multi_inheritance`: IntegrityError at `c2.save()` - UNIQUE constraint failed on `politician_ptr_id`

### Root Cause Analysis
In `django/db/models/base.py:807-819` (_save_parents method):
- Lines 807-809 sync pointer → parent pk only when parent pk is None AND pointer is not None
- No reverse sync when pointer IS None (should clear parent pk to enable new parent creation)
- Line 819 unconditionally overwrites pointer field with parent's pk after save
- Result: When user sets `p2.user_ptr_id = None`, the parent's `p2.id` remains the old value (1), causing an UPDATE instead of INSERT on parent, then pointer gets reset to old value (1), causing UNIQUE constraint violation on child INSERT

### Execution Trace (Profile example)
1. `p2.pk = None` → sets `profile_id = None`
2. `p2.user_ptr_id = None` → sets pointer to None  
3. `p2.id` = 1 (unchanged - this is the problem!)
4. In `_save_parents()`:
   - Line 808: `self.id` (parent pk) is 1, not None → no sync happens
   - User parent saved with pk=1 → UPDATE existing row (not INSERT new)
   - Line 819: `self.user_ptr_id = self.id = 1` → overwrites the None!
5. Profile INSERT with `user_ptr_id=1` → IntegrityError (value already exists)

### Edit Site
`django/db/models/base.py:807-809` - Add bidirectional sync between parent pointer field and parent pk field:
- When pointer is None, set parent pk to None (enables new parent creation)
- Existing logic: When parent pk is None but pointer is not None, sync pointer to parent pk

Confidence: deduction — 95%

## Craft gate-loop iteration 1: Divergent

**Patch:** Initial fix with `self._get_pk_val() is None` check in loop
**codex feedback:** Condition too broad, could break cases where parent pk deliberately set without parent pointer
**Gate:** First test passed, multi-inheritance test still failed with IntegrityError on politician_ptr_id
**Trajectory:** Divergent - error persists but evidence points to condition not triggering for Politician parent

## Craft gate-loop iteration 2: Debug

**Action:** Added debug logging to trace condition evaluation
**Evidence:** `CHECK: Congressman parent=Politician field_val=None parent_pk_val=None self_pk=1`
**Finding:** After saving Person parent (first iteration), Congressman's pk becomes 1 (person_ptr_id), so `self._get_pk_val()` returns 1 (not None) when processing Politician parent
**Root cause refined:** Condition `self._get_pk_val() is None` is unstable during parent loop - it changes after first parent save

## Craft gate-loop iteration 3: Fix with snapshot

**codex feedback:** Snapshot `child_pk_was_none = self._get_pk_val() is None` BEFORE the loop, use snapshot in condition instead of calling `self._get_pk_val()` during loop
**Patch:** 
```python
child_pk_was_none = self._get_pk_val() is None
for parent, field in meta.parents.items():
    if field:
        if field_val is None and parent_pk_val is not None and child_pk_was_none:
            setattr(self, parent._meta.pk.attname, None)
```
**Gate:** ✅ OK (expected failures=1) - both FAIL_TO_PASS tests pass
**Trajectory:** Convergent to green

## Audit (2026-05-23)

### FAIL_TO_PASS
- test_create_new_instance_with_pk_equals_none: **PASS** ✓
- test_create_new_instance_with_pk_equals_none_multi_inheritance: **PASS** ✓

### PASS_TO_PASS regressions
None. All 28 PASS_TO_PASS tests passed.

### Pre-existing (not counted)
- test_inheritance_values_joins: expected failure (intentional xfail, not a regression)

### Gate output
All 30 tests ran successfully with OK (expected failures=1). Both FAIL_TO_PASS tests that were failing on base with IntegrityError now pass. Zero regressions introduced.

VERDICT: RESOLVED
RE-ENTER: none
