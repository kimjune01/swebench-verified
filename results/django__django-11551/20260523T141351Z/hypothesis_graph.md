# Hypothesis graph: django__django-11551

## H₁ — Root cause identified (deduction, 95%)

**Symptom:** Test `test_valid_field_accessible_via_instance` fails with admin.E108 error for a PositionField that is only accessible via instance (raises AttributeError when accessed on the model class).

**Root cause:** Commit 47016adbf5 ("Fixed #28490 -- Removed unused code in admin.E108 check") removed the fallback logic in `django/contrib/admin/checks.py::_check_list_display_item` that checked `model._meta.get_field(item)` when `hasattr(model, item)` returns False.

**Code path:**
1. `_check_list_display_item` at line 718 validates list_display items
2. Line 723: `elif hasattr(obj.model, item):` - for PositionField, this is False because the field's `__get__` method raises AttributeError when instance is None
3. Line 738-749: The else clause immediately returns E108 without trying `model._meta.get_field(item)`
4. In the old code (before 47016adbf5), the else clause (lines 677-693) tried `model._meta.get_field(item)` and only returned E108 if it raised FieldDoesNotExist

**Evidence:**
- `django/contrib/admin/checks.py:718-749` — current implementation
- `git show 47016adbf5` — the problematic commit that removed the fallback
- The old code at lines 677-693 tried `model._meta.get_field(item)` in the else clause
- `model._meta.get_field()` uses internal field maps, not hasattr/getattr, so it works for PositionField

**Edit sites:**
- `django/contrib/admin/checks.py` lines 738-749: The else clause needs to try `model._meta.get_field(item)` before returning E108. If the field exists, check if it's a ManyToManyField (return E109) or valid (return []).

**Note:** The old code also had a bug - it didn't check for ManyToManyField in the else clause. The fix should include this check per the problem description's correctness table.

---

## Gate Loop - Iteration 1

**Pre-gate codex volley**: Confirmed approach is behaviorally correct. The fallback to `_meta.get_field()` when `hasattr(obj.model, item)` returns False is the right recovery path for fields whose class descriptors raise `AttributeError`.

**Applied fix**: Modified `django/contrib/admin/checks.py` lines 738-749. Replaced the immediate E108 return in the else clause with:
1. Try `obj.model._meta.get_field(item)`
2. If `FieldDoesNotExist` raised: return E108 (field doesn't exist)
3. If `ManyToManyField`: return E109 (not allowed in list_display)
4. Otherwise: return [] (valid field)

**Gate result**: ✓ PASS - All 120 tests passed including `test_valid_field_accessible_via_instance`

**Trajectory**: Convergent-success (first iteration, direct resolution)

**Status**: RESOLVED - The fix correctly handles fields accessible only via instance by checking `_meta.get_field()` as a fallback when `hasattr` returns False due to descriptor behavior.

---

## Audit: django__django-11551

**Patch confirmed live:**
```
django/contrib/admin/checks.py | 36 +++++++++++++++++++++++++-----------
1 file changed, 25 insertions(+), 11 deletions(-)
```

### FAIL_TO_PASS
- `test_valid_field_accessible_via_instance (modeladmin.test_checks.ListDisplayTests)`: **PASS** ✓

### PASS_TO_PASS regressions
None — all 120 tests passed cleanly.

### Pre-existing failures (confirmed against base capture)
None applicable — gate output shows no failures.

### Classification summary
- All FAIL_TO_PASS tests: ✓ PASS (1/1)
- PASS_TO_PASS regressions: 0
- Total test suite: 120/120 passing

The fix correctly restores the fallback logic that checks `model._meta.get_field(item)` when `hasattr(obj.model, item)` returns False. This handles fields whose descriptors raise AttributeError when accessed on the class (like PositionField), while still properly detecting ManyToManyField and truly missing fields.

VERDICT: RESOLVED
RE-ENTER: none
