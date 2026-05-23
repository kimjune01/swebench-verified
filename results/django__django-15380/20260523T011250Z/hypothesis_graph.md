# Hypothesis graph: django__django-15380

## H₀ (abduction)
**Status**: Root cause identified  
**Timestamp**: Initial diagnosis  
**Failure mode**: KeyError when migration autodetector processes simultaneous model and field rename

The test fails with:
```
KeyError: ('testapp', 'author')
  File "/testbed/django/db/migrations/autodetector.py", line 827, in generate_renamed_fields
    new_model_state = self.to_state.models[app_label, old_model_name]
```

## Root Cause (deduction - 99%)

**Bug location**: `django/db/migrations/autodetector.py:827`

When renaming both a model AND a field in the same migration, `generate_renamed_fields()` incorrectly looks up the model using the **old model name** in the **new state** (`to_state`).

The code does:
```python
old_model_name = self.renamed_models.get((app_label, model_name), model_name)
old_model_state = self.from_state.models[app_label, old_model_name]  # ✓ Correct
new_model_state = self.to_state.models[app_label, old_model_name]    # ✗ Wrong
```

But it should use the **new model name** when accessing `to_state`:
```python
new_model_state = self.to_state.models[app_label, model_name]  # ✓ Correct
```

**Evidence**:
1. Line 827 is the ONLY occurrence in the entire file where `to_state.models` is accessed with `old_model_name`
2. All 15 other uses of `to_state.models` use `model_name` (the new name)
3. All uses of `from_state.models` correctly use `old_model_name` (the old name)
4. Regression introduced in commit aa4acc164d when refactoring from model classes to model states

**Confidence**: Deduction - 99%  
This is a straightforward logic error visible from code inspection, confirmed by consistent patterns throughout the codebase.

## Edit Sites

**Single file, single line change**:
- `django/db/migrations/autodetector.py:827` - Change `old_model_name` to `model_name` in the `to_state.models` lookup

## Supporting Evidence

**Pattern analysis** (grep results):
- `to_state.models[...]` appears 16 times in autodetector.py
- Line 827 is the ONLY occurrence using `old_model_name` as the key
- All other 15 occurrences correctly use `model_name`

**Commit history**:
- Regression introduced in aa4acc164d "Fixed #29899 -- Made autodetector use model states instead of model classes"
- Before: `field = self.new_apps.get_model(app_label, model_name)._meta.get_field(field_name)` (used `model_name`)
- After: `new_model_state = self.to_state.models[app_label, old_model_name]` (incorrectly used `old_model_name`)
