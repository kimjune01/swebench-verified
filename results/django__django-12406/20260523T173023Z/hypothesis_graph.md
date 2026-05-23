# Hypothesis graph: django__django-12406

## H₀: Initial Hypothesis (Abduction)

**Timestamp:** 2026-05-23

The tests fail because `ModelChoiceField.__init__()` doesn't accept a `blank` parameter, and the logic for deciding whether to show a blank option doesn't account for the model field's `blank` attribute.

**Evidence:**
1. `test_choices_radio_blank` fails with: `TypeError: __init__() got an unexpected keyword argument 'blank'`
   - Location: `django/forms/models.py:1197` (in `Field.__init__` call)
   - Test passes `blank=blank` to `ModelChoiceField.__init__()` but the parameter doesn't exist

2. `test_non_blank_foreign_key_with_radio` fails with: `AssertionError: Lists differ: [('', '---------'), ...] != [(1, 'user')]`
   - Expected no blank option but got one
   - Model has: `character = models.ForeignKey(Character, models.SET_NULL, blank=False, null=True)`
   - Current logic in `ModelChoiceField.__init__()` (lines 1188-1191) only hides blank option if `required and (initial is not None)`

**Call path:**
- `ModelForm` → `fields_for_model()` → `f.formfield(**kwargs)` → `ForeignKey.formfield()` → `super().formfield()` → `Field.formfield()` (sets `required=not self.blank`) → `ModelChoiceField.__init__()`
- Widget is passed through kwargs from `Meta.widgets`

**Root cause:**
Current empty_label logic doesn't respect the model field's blank attribute. For RadioSelect widgets (or when explicitly specified), blank=False should mean no blank option shown.

**Confidence:** Deduction — 95%
- Traced the code path, read the exact error messages, identified the missing parameter and faulty logic


## Craft: Implementation (Gate Loop)

### Iteration 1: Initial Draft
**Hypothesis**: Add `blank` parameter to ModelChoiceField and pass from ForeignKey.formfield()

**Draft Approach**:
- Add `blank=None` parameter to ModelChoiceField.__init__()
- Update empty_label logic to: if blank=False, set empty_label=None
- Pass `'blank': self.blank` from ForeignKey.formfield()

**Codex Review #1**: 
- **Issue**: Would break non-radio FK fields by applying blank=False globally
- **Recommendation**: Only suppress empty_label for RadioSelect widgets, not all widgets
- **Recommendation**: Check widget type after Field.__init__() when self.widget is set

### Iteration 2: RadioSelect-Specific Check
**Revision**: Only apply blank logic for RadioSelect widgets

**Codex Review #2**:
- **Issue**: Precedence wrong - blank=True would override required+initial rule
- **Recommendation**: Combine conditions with OR instead of applying blank as override
- **Recommendation**: Move empty_label assignment before self.queryset = queryset

### Iteration 3: Final Implementation
**Implementation**:
```python
# django/forms/models.py - ModelChoiceField.__init__
# 1. Add blank=None parameter
# 2. Move empty_label logic after Field.__init__()
# 3. Combine conditions:
if (required and initial is not None) or (
    isinstance(self.widget, RadioSelect) and blank is False
):
    self.empty_label = None
else:
    self.empty_label = empty_label

# django/db/models/fields/related.py - ForeignKey.formfield
# Add 'blank': self.blank to kwargs
```

**Codex Review #3**: Approved - precedence correct, placement correct

**Gate Result**: ✅ PASS - All 169 tests passed
- test_choices_radio_blank: PASS
- test_non_blank_foreign_key_with_radio: PASS
- test_clean_model_instance: PASS

**Resolution**: RESOLVED - All FAIL_TO_PASS tests now pass, no regressions

## Audit: django__django-12406

**Timestamp:** 2026-05-23

### Phase 1: Patch Verification
✅ Patch is live in the tree:
- `django/db/models/fields/related.py`: +1 line (added `'blank': self.blank` to formfield kwargs)
- `django/forms/models.py`: +17/-6 lines (added blank parameter, refactored empty_label logic)

### Phase 2: Gate Execution
Full test suite run: **169 tests in 0.362s — OK**

### Phase 3: Result Classification

#### FAIL_TO_PASS (all must PASS)
✅ `test_non_blank_foreign_key_with_radio` (model_forms.tests.ModelFormBaseTest) — **PASS**
  - Baseline: FAIL (assertion error - blank option incorrectly shown)
  - After patch: PASS
  
✅ `test_choices_radio_blank` (model_forms.test_modelchoicefield.ModelChoiceFieldTests) — **PASS**
  - Baseline: ERROR (TypeError: unexpected keyword argument 'blank')
  - After patch: PASS (both blank=True and blank=False parameterized variants)
  
✅ `test_clean_model_instance` (model_forms.test_modelchoicefield.ModelChoiceFieldTests) — **PASS**
  - Baseline: ERROR (TypeError: unexpected keyword argument 'blank')
  - After patch: PASS

#### PASS_TO_PASS Regressions
**None** — all 169 tests passed in the gate run

#### Pre-existing Failures (not counted)
**None** — the baseline had 4 errors + 1 failure, all resolved by the patch

### Phase 4: Verdict

✅ **All FAIL_TO_PASS tests now pass** (3/3)
✅ **Zero PASS_TO_PASS regressions** (0)

The patch successfully:
1. Added the `blank` parameter to `ModelChoiceField.__init__()` to fix the TypeError
2. Correctly suppressed the empty option for RadioSelect widgets when `blank=False`
3. Preserved existing behavior for all other field/widget combinations

**Contract fulfilled:** All required tests pass, no regressions introduced.

