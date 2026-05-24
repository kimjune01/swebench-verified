# Hypothesis graph: django__django-15916

## H₀: Initial observation (abduction, 60%)

The tests fail because `formfield_callback` defined in `ModelForm.Meta` is not being used when constructing the form fields. Both failing tests expect fields to have `Textarea` widgets (from the custom callback), but they have `TextInput` widgets (the default).

**Evidence:**
- `test_custom_callback_in_meta`: Defines `Meta.formfield_callback` directly, expects it to be used
- `test_custom_callback_from_base_form_meta`: Uses `modelform_factory` with a base form that has `Meta.formfield_callback`, expects inheritance

Both fail with: `AssertionError: <class 'django.forms.widgets.TextInput'> != <class 'django.forms.widgets.Textarea'>`


## H₁: Root cause analysis (deduction, 95%)

**Issue 1: ModelFormMetaclass doesn't check Meta for formfield_callback**

In `django/forms/models.py:258-320`, `ModelFormMetaclass.__new__`:
- Line 266: `formfield_callback = attrs.pop("formfield_callback", base_formfield_callback)`
  - This pops from class-level attributes only
  - If user defines `class Meta: formfield_callback = callback`, it's not in `attrs`, so not found
- Line 273: `opts = ModelFormOptions(getattr(new_class, "Meta", None))`
  - At this point, `new_class.Meta.formfield_callback` exists but hasn't been checked
- Line 311: Passes the `formfield_callback` (still None) to `fields_for_model`

**Issue 2: modelform_factory overwrites inherited formfield_callback with None**

In `django/forms/models.py:563-650`, `modelform_factory`:
- Line 632: `bases = (form.Meta,) if hasattr(form, "Meta") else ()`
- Line 633: `Meta = type("Meta", bases, attrs)`
  - The new Meta class inherits from `form.Meta`, so it inherits `formfield_callback` if present
- Line 639: `form_class_attrs = {"Meta": Meta, "formfield_callback": formfield_callback}`
  - This explicitly sets class-level `formfield_callback` to the parameter value (None if not passed)
  - When `ModelFormMetaclass` runs, line 266 pops this None value, preventing it from finding the inherited Meta value

**Confirmed by code reading:**
- `ModelFormOptions` (line 245) doesn't extract `formfield_callback` from Meta options
- The metaclass checks base classes' Meta (line 262-263) but not the current class's Meta after it's created
- `modelform_factory` only sets `Meta.formfield_callback` if parameter is non-None (line 633-634)


## Edit Sites

**Site 1: `django/forms/models.py` lines 266-273 (ModelFormMetaclass)**
After creating `new_class` and `opts`, check if the current class's Meta has `formfield_callback` when the class-level callback is None.

Current:
```python
formfield_callback = attrs.pop("formfield_callback", base_formfield_callback)
new_class = super().__new__(mcs, name, bases, attrs)
...
opts = new_class._meta = ModelFormOptions(getattr(new_class, "Meta", None))
```

Fix: After line 273, add:
```python
if formfield_callback is None:
    if hasattr(new_class, 'Meta') and hasattr(new_class.Meta, 'formfield_callback'):
        formfield_callback = new_class.Meta.formfield_callback
```

**Site 2: `django/forms/models.py` line 639 (modelform_factory)**
Don't set class-level `formfield_callback` to None; only set it if explicitly provided or inherited from base form's Meta.

Current:
```python
form_class_attrs = {"Meta": Meta, "formfield_callback": formfield_callback}
```

Fix: Check if formfield_callback should be inherited:
```python
# Check if we should inherit formfield_callback from base form's Meta
if formfield_callback is None and hasattr(form, 'Meta') and hasattr(form.Meta, 'formfield_callback'):
    formfield_callback = form.Meta.formfield_callback

# Only set formfield_callback in class attrs if we have a value
form_class_attrs = {"Meta": Meta}
if formfield_callback is not None:
    form_class_attrs["formfield_callback"] = formfield_callback
```


## /craft gate loop

### Iteration 1: Initial fix

**Applied changes:**
1. Removed base class `Meta.formfield_callback` scan in `ModelFormMetaclass.__new__` (lines 260-263)
2. Changed `attrs.pop("formfield_callback", base_formfield_callback)` to `attrs.pop("formfield_callback", None)`
3. Added check after `opts` creation: if `formfield_callback is None`, check `new_class.Meta.formfield_callback`
4. In `modelform_factory`, only add `formfield_callback` to `form_class_attrs` if not None

**Rationale:**
The original code scanned base classes for `Meta.formfield_callback` before class creation, setting `formfield_callback` to the base value. This prevented the newly created class's own `Meta.formfield_callback` from being discovered. By removing the base scan and checking `new_class.Meta` after class creation, we let Python's normal Meta inheritance work (when a child Meta inherits from parent Meta, `new_class.Meta.formfield_callback` resolves to the correct value via MRO).

**codex review:**
Initial draft had redundant inheritance logic in `modelform_factory`. Simplified to just avoid setting `formfield_callback=None` in class attrs, allowing the metaclass to discover it from `Meta` inheritance.

**Gate result:** ✓ PASS (152 tests OK)

Both FAIL_TO_PASS tests now pass:
- `test_custom_callback_in_meta`: Form's own Meta.formfield_callback is used
- `test_custom_callback_from_base_form_meta`: Callback inherited through Meta inheritance works


## /audit verification

**Patch status:** Live (django/forms/models.py, 8 insertions, 8 deletions)

**Gate result:** All 152 tests passed

### FAIL_TO_PASS results
- test_custom_callback_from_base_form_meta (model_forms.tests.FormFieldCallbackTests): ✓ PASS
- test_custom_callback_in_meta (model_forms.tests.FormFieldCallbackTests): ✓ PASS

### PASS_TO_PASS regressions
None — all PASS_TO_PASS tests continue passing.

### Pre-existing failures
None observed in gate output.

**VERDICT:** RESOLVED
**RE-ENTER:** none

The fix correctly addresses both failure modes:
1. Direct Meta.formfield_callback definitions are discovered after class creation
2. Meta.formfield_callback inherited through Meta class inheritance works via normal Python MRO
3. No regressions introduced
