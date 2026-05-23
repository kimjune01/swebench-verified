# Hypothesis graph: django__django-12754

## H1: Missing dependency on RemoveField when creating subclass with moved field

**Type**: Abduction
**Confidence**: 90%

**Evidence**:
- Test failure shows operations in wrong order: `CreateModel` before `RemoveField` (expected reverse)
- File: `django/db/migrations/autodetector.py:565` - dependencies for CreateModel only include base model existence, not field removals
- File: `django/db/migrations/autodetector.py:337-355` - `_sort_migrations` uses `_auto_deps` for topological sort
- File: `django/db/migrations/autodetector.py:511-580` - `generate_created_models` sets dependencies but doesn't check for field name conflicts with base model removals

**Root cause**:
When `generate_created_models` creates a new model that inherits from a base, it adds a dependency on the base model existing (`(base_app_label, base_name, None, True)`), but it doesn't check if any of the new model's fields have the same name as fields being removed from the base model. This causes the `CreateModel` operation to run before the `RemoveField` operation, creating a field clash at migrate time.

**Fix location**:
`django/db/migrations/autodetector.py:565-575` - After adding dependency on base models, add check for field name conflicts with removed base model fields and add dependencies on those removals.

**Required logic**:
For each base model:
1. Check if base exists in old state (`self.from_state.models`)
2. For each field in the new model being created
3. Check if that field name existed in the old base model
4. Check if that field name is NOT in the new base model (i.e., being removed)
5. If all true, add dependency: `(base_app_label, base_model_name, field_name, False)`

## Gate Loop - Iteration 1

**Fix applied:** Added dependency logic in `generate_created_models` to check if any fields in a new model being created existed in a base model in the old state but not in the new state. When detected, adds a RemoveField dependency `(base_app_label, base_name, field_name, False)` to ensure RemoveField operations happen before CreateModel.

**Changes:**
- `django/db/migrations/autodetector.py` lines 567-578: Added loop after "Depend on all bases" that:
  1. Iterates through each base in `model_state.bases`
  2. Checks if base exists in both `from_state` and `to_state`
  3. For each non-related field in the new model, checks if it existed in old base but not in new base
  4. If so, adds dependency on field removal: `dependencies.append((base_app_label, base_name, field_name, False))`

**codex feedback incorporated:**
- Use `base_name` (not `.lower()`) in dependency tuple to match existing code style
- Compute `base_key` once instead of duplicating `old_base_key` and `new_base_key`
- Only check fields not in `related_fields` to avoid dependencies on fields not actually emitted in CreateModel

**Gate result:** ✅ PASSED
- All 116 tests passed in 0.205s
- FAIL_TO_PASS test `test_add_model_with_field_removed_from_base_model` now passes
- No regressions

**Status:** RESOLVED - The fix correctly orders RemoveField before CreateModel when a field moves from base to subclass.

## Audit Report - django__django-12754

**Patch status**: Live in tree (13 lines added to `django/db/migrations/autodetector.py`)

**Gate execution**: Full test suite run - `./tests/runtests.py migrations.test_autodetector`

### FAIL_TO_PASS

- `test_add_model_with_field_removed_from_base_model (migrations.test_autodetector.AutodetectorTests)`: **PASS** ✓

### PASS_TO_PASS regressions

None. All 116 tests in the suite passed.

### Pre-existing failures (not counted, confirmed against base capture)

None. The fail-on-base capture showed all tests passing except the FAIL_TO_PASS test, which now passes.

### Classification

- **FAIL_TO_PASS coverage**: 1/1 tests now passing (100%)
- **Regression count**: 0
- **Test suite health**: 116/116 passing

### Patch summary

The fix adds dependency tracking in `generate_created_models()` (lines 566-578) to detect when a field in a new model existed in its base model's old state but not in its new state (indicating the field was removed from the base). When this pattern is detected, the fix adds an explicit dependency on the `RemoveField` operation, ensuring proper operation ordering.

**Key logic**:
1. After adding base model dependencies, iterate through each base
2. For bases present in both old and new state, compare field sets
3. For each non-related field in the new model that existed in old base but not new base
4. Add dependency: `(base_app_label, base_name, field_name, False)` to ensure RemoveField runs first

This prevents the migration operation ordering bug where `CreateModel` would execute before `RemoveField`, causing a field name collision at migrate time.

VERDICT: RESOLVED
RE-ENTER: none
