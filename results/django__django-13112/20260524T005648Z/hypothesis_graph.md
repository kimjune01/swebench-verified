# Hypothesis graph: django__django-13112

## H₀: Initial observation (abduction, 60%)
The tests fail because ForeignKey lazy references lowercase the entire app_label when the target is a string reference, causing a mismatch with mixed-case app labels.

Error: `ValueError: The field MiXedCase_migrations.Book.author was declared with a lazy reference to 'mixedcase_migrations.author', but app 'mixedcase_migrations' isn't installed.`

The actual app is registered as 'MiXedCase_migrations' but the lazy reference is looking for 'mixedcase_migrations'.

## H₁: Root cause identified (deduction, 95%)

**Location**: `django/db/models/fields/related.py:585`

**Problem**: In `ForeignKey.deconstruct()`, when `self.remote_field.model` is a string (e.g., 'MiXedCase_migrations.Author'), the entire string is lowercased:

```python
if isinstance(self.remote_field.model, str):
    kwargs['to'] = self.remote_field.model.lower()  # BUG: lowercases app_label too!
else:
    kwargs['to'] = self.remote_field.model._meta.label_lower
```

**Why this happens**:
1. When `ModelState.from_model(Book)` is called, the ForeignKey is cloned via `field.clone()`
2. `clone()` calls `deconstruct()`, which sees `Author` is a class and uses `label_lower`, producing 'MiXedCase_migrations.author'
3. A new ForeignKey is created with `to='MiXedCase_migrations.author'` (string)
4. When `ModelState.render()` is called, it clones fields again: `{name: field.clone() for name, field in self.fields.items()}`
5. This second `deconstruct()` sees `remote_field.model` is now a string 'MiXedCase_migrations.author'
6. Line 585 lowercases the **entire string** to 'mixedcase_migrations.author'
7. The lazy reference uses this lowercase string, creating key `('mixedcase_migrations', 'author')`
8. But the model was registered with key `('MiXedCase_migrations', 'author')`
9. Key mismatch → lazy reference cannot be resolved → error

**Supporting evidence**:
- `django/db/models/fields/related.py:585` — lowercases entire string without preserving app_label case
- `django/db/models/options.py:135` — `label_lower` property returns `'%s.%s' % (self.app_label, self.model_name)` (preserves app_label case, only model_name is lowercase)
- `django/db/models/utils.py:11-12` — when string is split: `app_label, model_name = model.split(".")` then `model_tuple = app_label, model_name.lower()` (preserves app_label case from split)

The inconsistency: `label_lower` preserves app_label case, but `str.lower()` on line 585 lowercases everything.


## Gate Loop - Iteration 1

**Fix applied**: Modified `ForeignKey.deconstruct()` in `django/db/models/fields/related.py` line 585 to preserve app_label case when `remote_field.model` is a string.

Changed:
```python
if isinstance(self.remote_field.model, str):
    kwargs['to'] = self.remote_field.model.lower()
```

To:
```python
if isinstance(self.remote_field.model, str):
    # Only lowercase the model name, not the app_label
    if '.' in self.remote_field.model:
        app_label, model_name = self.remote_field.model.split('.', 1)
        kwargs['to'] = '%s.%s' % (app_label, model_name.lower())
    else:
        # Bare model name without app_label
        kwargs['to'] = self.remote_field.model.lower()
```

**Codex feedback**: Suggested checking ManyToManyField for the same issue, but verification showed ManyToManyField.deconstruct() already preserves the string as-is (no lowercasing).

**Gate result**: ✓ PASS - All 64 tests passed including FAIL_TO_PASS test `test_reference_mixed_case_app_label`

**Status**: RESOLVED - Fix correctly preserves app_label case while lowercasing only the model name portion, consistent with `make_model_tuple` behavior.

---

# Audit: django__django-13112

## FAIL_TO_PASS
- `test_reference_mixed_case_app_label (migrations.test_state.StateTests)`: **PASS** ✓

## PASS_TO_PASS regressions
None. All 63 PASS_TO_PASS tests remain passing.

## Pre-existing failures (not counted, confirmed against base capture)
None. All tests passing on base remain passing.

## Patch summary
```diff
diff --git a/django/db/models/fields/related.py b/django/db/models/fields/related.py
@@ -582,7 +582,13 @@ class ForeignObject(RelatedField):
         if self.remote_field.parent_link:
             kwargs['parent_link'] = self.remote_field.parent_link
         if isinstance(self.remote_field.model, str):
-            kwargs['to'] = self.remote_field.model.lower()
+            # Only lowercase the model name, not the app_label
+            if '.' in self.remote_field.model:
+                app_label, model_name = self.remote_field.model.split('.', 1)
+                kwargs['to'] = '%s.%s' % (app_label, model_name.lower())
+            else:
+                # Bare model name without app_label
+                kwargs['to'] = self.remote_field.model.lower()
         else:
             kwargs['to'] = self.remote_field.model._meta.label_lower
```

The fix splits the string reference on the dot, preserves the app_label case, and only lowercases the model name. This matches the behavior of `make_model_tuple` and `label_lower`, ensuring lazy references resolve correctly with mixed-case app labels.

VERDICT: RESOLVED
RE-ENTER: none
