# Hypothesis graph: django__django-14534

## H₀: Initial hypothesis (abduction)
**Created**: 2026-05-22
**Mode**: Abduction
**Status**: Confirmed → Root Cause

The tests fail because `BoundWidget.id_for_label` hardcodes the ID format as `'id_%s_%s' % (name, index)` instead of using the ID already computed and stored in `self.data['attrs']['id']`.

**Evidence**:
- Test failure 1: Expected `'prefix_field_0'` but got `'id_field_0'` - the custom `auto_id='prefix_%s'` prefix is being ignored
- Test failure 2: Expected `None` but got `'id_name_0'` - an ID is being generated even when `auto_id=False`

**Trace from test to failure**:
1. Test creates form with `auto_id='prefix_%s'` or `auto_id=False`
2. Accesses `form['field'].subwidgets[0].id_for_label`
3. `BoundField.subwidgets` (boundfield.py:35) computes `id_ = self.auto_id` and passes `attrs={'id': id_}` to `widget.subwidgets()`
4. `ChoiceWidget.create_option` (widgets.py:~610) properly formats ID with index: `option_attrs['id'] = self.id_for_label(option_attrs['id'], index)` and stores in returned dict
5. `BoundWidget.id_for_label` (boundfield.py:288) **ignores** `self.data['attrs']['id']` and reconstructs: `'id_%s_%s' % (self.data['name'], self.data['index'])`

**Root cause confirmed**: Line 288 in django/forms/boundfield.py


## Craft gate-loop

### Iteration 1: Initial fix

**Hypothesis**: Change `BoundWidget.id_for_label` to return `self.data.get('attrs', {}).get('id')` instead of hardcoding `'id_%s_%s'` format.

**Codex pre-gate review**: Approved with defensive guards - use `self.data.get('attrs', {}).get('id')` instead of `self.data['attrs'].get('id')` to handle custom widgets that might not include 'attrs' key.

**Applied diff**:
```diff
--- a/django/forms/boundfield.py
+++ b/django/forms/boundfield.py
@@ -277,7 +277,7 @@ class BoundWidget:
 
     @property
     def id_for_label(self):
-        return 'id_%s_%s' % (self.data['name'], self.data['index'])
+        return self.data.get('attrs', {}).get('id')
 
     @property
     def choice_label(self):
```

**Gate result**: ✅ PASS - All 121 tests passed including both FAIL_TO_PASS tests:
- `test_boundfield_subwidget_id_for_label` - passes (returns 'prefix_field_0' with auto_id='prefix_%s')
- `test_iterable_boundfield_select` - passes (returns None with auto_id=False)

**Trajectory**: Convergent (immediate resolution)

**Verdict**: Root cause correctly identified. Fix minimal and complete. No regressions.

## Audit: django__django-14534
**Executed**: 2026-05-22
**Patch status**: Live (1 file changed, 1 insertion, 1 deletion)

### Gate results
Ran 121 tests in 0.132s - **ALL PASSED**

### FAIL_TO_PASS classification
- ✅ `test_form_with_iterable_boundfield_id` - **PASS** (formerly: "If auto_id is provided when initializing the form, the generated ID in...")
- ✅ `test_iterable_boundfield_select` - **PASS**

### PASS_TO_PASS regressions
**None** - All PASS_TO_PASS tests remain passing:
- test_attribute_class, test_attribute_instance, test_attribute_override ✓
- test_default, test_kwarg_class, test_kwarg_instance ✓
- test_accessing_clean, test_auto_id, test_auto_id_false ✓
- test_auto_id_on_form_and_field, test_auto_id_true ✓
- (All 121 tests passed with zero failures)

### Pre-existing failures
**None** - Baseline comparison shows no pre-existing failures carried forward.

### Verdict summary
- ✅ All FAIL_TO_PASS tests now pass
- ✅ Zero PASS_TO_PASS regressions
- ✅ Clean gate run

The fix correctly addresses the root cause: `BoundWidget.id_for_label` now returns the ID computed by the form's `auto_id` setting (stored in `self.data['attrs']['id']`) instead of hardcoding the `'id_%s_%s'` format. Both test cases (custom prefix and auto_id=False) now behave correctly.

VERDICT: RESOLVED
RE-ENTER: none
