# Hypothesis graph: django__django-14725

## Hypothesis H0 (abduction, 85%)

**Failure mode**: TypeError - `modelformset_factory()` and `inlineformset_factory()` reject the `edit_only` keyword argument because it doesn't exist in their parameter lists.

**Root cause**: The `edit_only` feature is not implemented. Three functions need to accept and propagate the parameter:
1. `formset_factory` (django/forms/formsets.py:478) - needs to accept `edit_only` and set it as a class attribute
2. `modelformset_factory` (django/forms/models.py:872) - needs to accept `edit_only` and pass it to `formset_factory`
3. `inlineformset_factory` (django/forms/models.py:1072) - needs to accept `edit_only` and pass it via kwargs to `modelformset_factory`

**Behavior change needed**: `BaseModelFormSet.save_new_objects` (django/forms/models.py:814) must check `self.edit_only` and skip saving new objects when True.

**Evidence**:
- django/forms/formsets.py:478-481 - `formset_factory` parameters don't include `edit_only`
- django/forms/formsets.py:498-501 - attrs dict sets `can_delete`, `can_order` as class attributes
- django/forms/models.py:872-878 - `modelformset_factory` parameters don't include `edit_only`
- django/forms/models.py:895-898 - call to `formset_factory` passes existing boolean flags
- django/forms/models.py:1072-1080 - `inlineformset_factory` parameters don't include `edit_only`
- django/forms/models.py:1093-1112 - kwargs dict for `modelformset_factory` includes similar flags
- django/forms/models.py:814-827 - `save_new_objects` iterates `extra_forms` unconditionally

**Confidence**: Deduction, 95% - traced call path from test through all three factories to the save method. Pattern matches existing `can_delete`/`can_order` implementation.


## Craft: Gate Loop

### Iteration 1: Initial Implementation

**Applied changes:**
1. Added `edit_only=False` parameter to `formset_factory` signature (django/forms/formsets.py:478)
2. Added `'edit_only': edit_only` to attrs dict in `formset_factory` (django/forms/formsets.py:498)
3. Added early return in `BaseModelFormSet.save_new_objects` to return empty list when `edit_only=True` (django/forms/models.py:814)
4. Added `edit_only=False` parameter to `modelformset_factory` signature (django/forms/models.py:872)
5. Passed `edit_only=edit_only` to `formset_factory` call in `modelformset_factory` (django/forms/models.py:895)
6. Added `edit_only=False` parameter to `inlineformset_factory` signature (django/forms/models.py:1072)
7. Added `'edit_only': edit_only` to kwargs dict in `inlineformset_factory` (django/forms/models.py:1093)

**Gate result:** ✅ PASS

All 67 tests passed, including the three FAIL_TO_PASS tests:
- test_edit_only
- test_edit_only_inlineformset_factory  
- test_edit_only_object_outside_of_queryset

**Resolution:** The recon diagnosis was correct. The implementation followed the established pattern for boolean flags like `can_delete`, adding the parameter through all three factory functions and setting it as a class attribute. The `save_new_objects` method checks the flag and returns an empty list when `edit_only=True`, preventing new object creation while allowing edits to existing objects.


## Audit: django__django-14725

### FAIL_TO_PASS (all must pass)
- test_edit_only (model_formsets.tests.ModelFormsetTest): **PASS** ✓
- test_edit_only_inlineformset_factory (model_formsets.tests.ModelFormsetTest): **PASS** ✓
- test_edit_only_object_outside_of_queryset (model_formsets.tests.ModelFormsetTest): **PASS** ✓

### PASS_TO_PASS regressions
**None** — all 64 PASS_TO_PASS tests remain passing.

### Pre-existing failures (not counted)
**None** — the fail-on-base capture showed the 3 FAIL_TO_PASS tests as ERRORs (missing `edit_only` parameter), no other failures.

### Verdict
All FAIL_TO_PASS tests now pass. Zero regressions. The patch correctly implements the `edit_only` parameter across all three factory functions and enforces the behavior in `save_new_objects`.

VERDICT: RESOLVED
RE-ENTER: none
