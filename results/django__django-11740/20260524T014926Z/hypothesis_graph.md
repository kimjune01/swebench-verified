# Hypothesis graph: django__django-11740

## H1: Missing FK dependency check in AlterField operation
**Status**: Active
**Type**: Abduction → Deduction (traced code path)
**Confidence**: 95%

### Evidence
1. Test `test_alter_field_to_fk_dependency_other_app` fails with:
   - Expected: AlterField migration with dependency `[('testapp', '__first__')]`
   - Actual: AlterField migration with dependency `None`

2. Code comparison in `django/db/migrations/autodetector.py`:
   - `_generate_added_field` (line 852-881): **DOES** check for FK and add dependencies via `_get_dependencies_for_foreign_key(field)`
   - `generate_altered_fields` (line 906-978): **DOES NOT** check for FK dependencies when creating AlterField operations

### Root cause
In `generate_altered_fields` method, when creating an `AlterField` operation (line 966), the code calls:
```python
self.add_operation(
    app_label,
    operations.AlterField(
        model_name=model_name,
        name=field_name,
        field=field,
        preserve_default=preserve_default,
    )
)
```

It never checks if `new_field` has a `remote_field` (FK/M2M relationship) and never calls `_get_dependencies_for_foreign_key(new_field)` to add the required dependencies.

### Edit site
`django/db/migrations/autodetector.py` lines 954-973: Before calling `self.add_operation`, add logic to:
1. Check if `new_field` (or the `field` variable) has a `remote_field` and `remote_field.model`
2. If yes, calculate dependencies using `self._get_dependencies_for_foreign_key(field)` 
3. Pass the dependencies to `self.add_operation(..., dependencies=dependencies)`

### Supporting code quotes
- `django/db/migrations/autodetector.py:856-858`:
  ```python
  if field.remote_field and field.remote_field.model:
      dependencies.extend(self._get_dependencies_for_foreign_key(field))
  ```
  This pattern exists in `_generate_added_field` but is missing in `generate_altered_fields`

- `django/db/migrations/autodetector.py:1060-1077`: `_get_dependencies_for_foreign_key` method that returns proper dependencies for FK fields

## Gate iteration 1 — PASS

**Applied fix:**
Added FK dependency checking to `generate_altered_fields` method in `django/db/migrations/autodetector.py` (lines 966-969):
- Initialize `dependencies = []`
- Check `if field.remote_field and field.remote_field.model:`
- Call `dependencies.extend(self._get_dependencies_for_foreign_key(field))`
- Pass `dependencies=dependencies` to `self.add_operation()` call

**codex review:** Approved. Pattern mirrors `_generate_added_field` correctly. No behavioral breaks for non-relational fields.

**Gate result:** ✅ PASS
- All 113 tests passed in 0.176s
- FAIL_TO_PASS test `test_alter_field_to_fk_dependency_other_app` now passes
- No regressions detected

**Trajectory:** Convergent (single iteration success)

**Resolution:** RESOLVED — The fix correctly adds dependencies for AlterField operations when the new field has a foreign key relationship to another app, matching the existing behavior in AddField operations.

---

## Audit: django__django-11740

### Patch verification
```diff
django/db/migrations/autodetector.py | 7 ++++++-
 1 file changed, 6 insertions(+), 1 deletion(-)
```

Patch adds FK dependency tracking to AlterField operations (lines 966-978).

### Gate execution
Full test suite: **113 tests in 0.186s — OK**

### FAIL_TO_PASS
- `test_alter_field_to_fk_dependency_other_app`: **PASS** ✓

### PASS_TO_PASS regressions
**None** — All 113 tests passed.

### Pre-existing failures
**None** — Baseline capture also showed all tests passing.

### Classification
- All FAIL_TO_PASS tests now pass: ✓
- Zero regressions introduced: ✓
- Contract fully satisfied

VERDICT: RESOLVED
RE-ENTER: none
