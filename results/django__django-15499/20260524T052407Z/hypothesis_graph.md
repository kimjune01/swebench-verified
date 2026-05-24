# Hypothesis graph: django__django-15499

## Hypothesis H0 - Initial Diagnosis
**Status**: Active  
**Type**: Abduction  
**Confidence**: 95% (deduction from code reading)

### Observation
The test `test_create_alter_model_managers` fails because the optimizer does not reduce `CreateModel + AlterModelManagers` into a single `CreateModel` operation. The optimizer returns both operations unchanged instead of merging them.

### Root Cause
The `CreateModel.reduce()` method in `django/db/migrations/operations/models.py` (lines 104-240) handles reduction with `AlterModelOptions` (lines 152-167) but is **missing** a similar handler for `AlterModelManagers`.

### Supporting Evidence
- `django/db/migrations/operations/models.py:152-167` - Shows the pattern for handling `AlterModelOptions`:
  ```python
  elif (
      isinstance(operation, AlterModelOptions)
      and self.name_lower == operation.name_lower
  ):
      options = {**self.options, **operation.options}
      # ... merging logic ...
      return [CreateModel(..., options=options, ...)]
  ```
- `django/db/migrations/operations/models.py:732-758` - `AlterModelManagers` class has a `managers` attribute (line 738)
- No `isinstance(operation, AlterModelManagers)` check exists in `CreateModel.reduce()`
- Test `test_create_alter_model_options` passes (lines 117-132 of test file), confirming the pattern works for options

### Edit Sites
**Primary**: `django/db/migrations/operations/models.py`, lines 168-180 (after the `AlterModelOptions` elif block)

Add a new `elif` clause:
```python
elif (
    isinstance(operation, AlterModelManagers)
    and self.name_lower == operation.name_lower
):
    return [
        CreateModel(
            self.name,
            fields=self.fields,
            options=self.options,
            bases=self.bases,
            managers=operation.managers,
        ),
    ]
```

This follows the exact same pattern as `AlterModelOptions` but simpler (no dict merging needed - just replace the managers list).


## /craft iteration 1

**Hypothesis**: Add AlterModelManagers handler to CreateModel.reduce() following the existing AlterModelOptions pattern.

**Edit**: Inserted elif clause in `django/db/migrations/operations/models.py:173` to handle `AlterModelManagers` operations by folding them into `CreateModel` with `managers=operation.managers`.

**Gate result**: ✅ PASS — All 36 optimizer tests passed, including `test_create_alter_model_managers`.

**Evidence shape**: Convergent success — test passed on first gate run after fix applied.

**Codex feedback**: "No functional problem in the proposed diff. It matches the existing AlterModelOptions folding pattern and preserves fields, options, and bases while replacing only managers."

## Audit — django__django-15499

### FAIL_TO_PASS
- `test_create_alter_model_managers`: ✅ **PASS** (was FAIL on base)

### PASS_TO_PASS regressions
None. All 35 PASS_TO_PASS tests remain passing.

### Pre-existing failures (not counted)
None. The baseline had only one failure (test_create_alter_model_managers), which is now fixed.

### Classification
All 36 tests in the suite passed:
- The single FAIL_TO_PASS target is now passing
- Zero PASS_TO_PASS regressions introduced
- The fix correctly handles `CreateModel + AlterModelManagers` reduction

The craft patch added 13 lines to `django/db/migrations/operations/models.py`, implementing an `elif` clause in `CreateModel.reduce()` that folds `AlterModelManagers` operations into the `CreateModel` by setting `managers=operation.managers`, following the exact pattern already established for `AlterModelOptions`.

VERDICT: RESOLVED
RE-ENTER: none
