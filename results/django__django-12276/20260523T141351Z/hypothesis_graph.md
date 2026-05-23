# Hypothesis graph: django__django-12276

## Hypothesis Node 1: FileInput missing use_required_attribute method
**Type:** abduction → deduction  
**Status:** active  
**Timestamp:** 2026-05-23

### Observation
Two tests fail:
1. `test_use_required_attribute` - `widget.use_required_attribute('resume.txt')` returns `True` but should return `False`
2. `test_filefield_with_fileinput_required` - FileInput renders `<input type="file" name="file1" required>` when it should render `<input type="file" name="file1">` (no required) when initial data exists

### Diagnosis
FileInput class (django/forms/widgets.py:374) doesn't override `use_required_attribute`, so it inherits from Widget (line 275) which returns `not self.is_hidden` without checking for initial data.

ClearableFileInput (line 454) correctly overrides this:
```python
def use_required_attribute(self, initial):
    return super().use_required_attribute(initial) and not initial
```

The boundfield.py:224 calls `widget.use_required_attribute(self.initial)` to determine if the `required` HTML attribute should be added.

**Root cause:** FileInput lacks the `use_required_attribute` method that checks for initial data.

**Confidence:** deduction - 95%

### Supporting evidence
- `django/forms/widgets.py:275` - Widget.use_required_attribute returns `not self.is_hidden`
- `django/forms/widgets.py:374-390` - FileInput class has no use_required_attribute override
- `django/forms/widgets.py:454-455` - ClearableFileInput.use_required_attribute properly checks initial
- `django/forms/boundfield.py:224` - Call site passes self.initial to widget method

### Edit sites
- `django/forms/widgets.py` lines 374-390: Add `use_required_attribute` method to FileInput class with implementation: `return super().use_required_attribute(initial) and not initial`


## Craft Gate Loop

### Iteration 1: Initial implementation

**Change applied:**
Added `use_required_attribute` method to FileInput class at line 390-391:
```python
def use_required_attribute(self, initial):
    return super().use_required_attribute(initial) and not initial
```

**Codex review:** No functional issues. Patch correctly matches ClearableFileInput behavior. ClearableFileInput will apply `and not initial` twice (redundant but harmless).

**Gate result:** ✅ GREEN - All 119 tests passed
- test_use_required_attribute (forms_tests.widget_tests.test_fileinput.FileInputTest) ... ok
- test_filefield_with_fileinput_required (forms_tests.tests.test_forms.FormsTestCase) ... ok

**Trajectory:** Convergent - FAIL_TO_PASS tests now pass

**Resolution:** RESOLVED - Both FAIL_TO_PASS tests pass, no regressions

## Audit: django__django-12276

### Patch verification
Patch is live in tree:
```
django/forms/widgets.py | 3 +++
1 file changed, 3 insertions(+)
```

Added `use_required_attribute` method to FileInput class that returns `False` when initial data exists.

### Gate results (119 tests)
All tests passed. Full gate run: **OK**

### FAIL_TO_PASS results
✅ test_use_required_attribute (forms_tests.widget_tests.test_fileinput.FileInputTest) - **PASS**
✅ test_filefield_with_fileinput_required (forms_tests.tests.test_forms.FormsTestCase) - **PASS**

### PASS_TO_PASS regressions
**None** - All PASS_TO_PASS tests remain passing:
- test_attribute_class (RendererTests) - ok
- test_attribute_instance (RendererTests) - ok
- test_attribute_override (RendererTests) - ok
- test_default (RendererTests) - ok
- test_kwarg_class (RendererTests) - ok
- test_kwarg_instance (RendererTests) - ok
- test_render (FileInputTest) - ok
- test_value_omitted_from_data (FileInputTest) - ok
- All other forms_tests - ok

### Pre-existing failures
**None** - The fail-on-base capture showed only one pre-existing failure (test_filefield_with_fileinput_required), which is now resolved.

### Verdict
**RESOLVED** - All FAIL_TO_PASS tests now pass, zero PASS_TO_PASS regressions introduced.

