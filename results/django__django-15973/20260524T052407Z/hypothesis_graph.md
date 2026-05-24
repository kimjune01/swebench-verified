# Hypothesis graph: django__django-15973

## H1: Wrong dependency calculation for through model (ABDUCTION - 90%)
**Status**: Active hypothesis
**Type**: Root cause identified

The bug is in `django/db/migrations/autodetector.py` at line 1426 in the `_get_dependencies_for_foreign_key` method.

When calculating dependencies for a ManyToManyField with a through model, the code incorrectly uses `remote_field_model` (the M2M target model) instead of `field.remote_field.through` (the actual through model):

```python
# Line 1424-1430 (BUGGY)
if getattr(field.remote_field, "through", None):
    through_app_label, through_object_name = resolve_relation(
        remote_field_model,  # BUG: This is the M2M target, not the through model!
        app_label,
        model_name,
    )
    dependencies.append((through_app_label, through_object_name, None, True))
```

**Impact cascade**:
1. When Author (authors app) has M2M to Publisher (testapp) through Contract (contract app)
2. The dependency calculation resolves `remote_field_model` ("testapp.Publisher") instead of `field.remote_field.through` ("contract.Contract")
3. AddField operation gets dependency on ("testapp", "publisher") instead of ("contract", "contract")
4. `_build_migration_list` doesn't detect the cross-app dependency on the contract app
5. Both CreateModel and AddField stay in the same operation list for authors app
6. They get placed in the same migration
7. The optimizer merges AddField back into CreateModel (no in-between operations to block it)
8. Result: 1 migration with M2M field in CreateModel, instead of 2 migrations with M2M split into AddField

**Evidence**:
- Line 244: Correctly uses `field.remote_field.through` when building through_users map
- Test expects dependency on all three apps: authors, contract, testapp
- Actual behavior shows only 1 authors migration (should be 2)

**Fix location**: Line 1426 should use `field.remote_field.through` instead of `remote_field_model`

## Craft gate loop

### Iteration 1: Draft and apply fix

**Edit**: Changed line 1425 in `django/db/migrations/autodetector.py` from `remote_field_model` to `field.remote_field.through`

**Codex pre-gate review**: Confirmed fix is correct. The second `resolve_relation()` must use `field.remote_field.through`, not `remote_field_model`; otherwise the through dependency is just a duplicate dependency on the M2M target.

**Gate result**: ✅ PASS — All 165 tests passed in 0.067s

**Trajectory**: Convergent success — FAIL_TO_PASS test now passes

**Resolution**: The one-line fix correctly resolves the M2M through model dependency calculation, allowing `_build_migration_list` to properly split the M2M field into a separate migration when the through model is in a different app.

## Audit: django__django-15973

### FAIL_TO_PASS
- `test_create_with_through_model_separate_apps (migrations.test_autodetector.AutodetectorTests)`: **PASS** ✅

### PASS_TO_PASS regressions
None - all 165 tests in the full suite passed.

### Pre-existing failures (not counted)
None confirmed against base capture.

### Gate results
- Full suite: 165 tests ran in 0.066s - all passed
- Targeted FAIL_TO_PASS test: Verified passing in isolated run

### Contract verification
✅ All FAIL_TO_PASS tests pass (1/1)
✅ Zero PASS_TO_PASS regressions (0 regressions)

