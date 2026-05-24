# Hypothesis graph: django__django-14915

## H₁: Missing __hash__ method (abduction)

**Observation**: Test fails with `TypeError: unhashable type: 'ModelChoiceIteratorValue'` when calling `hash()` on a `ModelChoiceIteratorValue` instance.

**Root cause**: `ModelChoiceIteratorValue` class (django/forms/models.py:1161) defines `__eq__` but not `__hash__`. In Python, defining `__eq__` without `__hash__` causes `__hash__` to be set to `None`, making the type unhashable.

**Evidence**:
- django/forms/models.py:1161-1172: Class defines `__init__`, `__str__`, and `__eq__` but no `__hash__`
- django/forms/models.py:1170-1172: `__eq__` compares based on `self.value`
- Python data model: Classes defining `__eq__` must also define `__hash__` to remain hashable

**Proposed fix**: Add `__hash__` method to `ModelChoiceIteratorValue` that returns `hash(self.value)`, consistent with the `__eq__` implementation.

**Confidence**: Deduction — 99%

**Edit sites**:
- django/forms/models.py:1161-1172: Add `__hash__` method after `__eq__`


## craft gate loop

### Iteration 1

**Hypothesis**: Add `__hash__` method returning `hash(self.value)` to `ModelChoiceIteratorValue` class

**Edit**: Added `__hash__` method to `django/forms/models.py` after `__eq__` method (line 1173-1174)

**codex volley**: "No functional issue with the proposed diff. `__hash__ = hash(self.value)` matches the existing `__eq__` semantics and fixes the unhashable-instance failure."

**Gate outcome**: ✓ PASS — all 24 tests passed, including `test_choice_value_hash`

**Trajectory**: convergent-resolved

**Result**: FAIL_TO_PASS test now passes. Fix complete.

## Audit: django__django-14915

### Phase 1: Patch verification
Patch is live: django/forms/models.py modified (+3 lines)
- Added `__hash__` method to `ModelChoiceIteratorValue` class

### Phase 2: Gate execution
Ran full test suite: 24 tests in model_forms.test_modelchoicefield

### Phase 3: Classification

**FAIL_TO_PASS results:**
- test_choice_value_hash: **PASS** ✓ (was ERROR on base with `TypeError: unhashable type: 'ModelChoiceIteratorValue'`)

**PASS_TO_PASS results:**
All 23 tests PASS:
- test_basics: ok
- test_choice_iterator_passes_model_to_widget: ok
- test_choices: ok
- test_choices_bool: ok
- test_choices_bool_empty_label: ok
- test_choices_freshness: ok
- test_choices_not_fetched_when_not_rendering: ok
- test_choices_radio_blank: ok
- test_clean_model_instance: ok
- test_clean_to_field_name: ok
- test_custom_choice_iterator_passes_model_to_widget: ok
- test_deepcopies_widget: ok
- test_disabled_modelchoicefield: ok
- test_disabled_modelchoicefield_has_changed: ok
- test_disabled_modelchoicefield_initial_model_instance: ok
- test_disabled_modelmultiplechoicefield_has_changed: ok
- test_disabled_multiplemodelchoicefield: ok
- test_no_extra_query_when_accessing_attrs: ok
- test_num_queries: ok
- test_overridable_choice_iterator: ok
- test_queryset_manager: ok
- test_queryset_none: ok
- test_result_cache_not_shared: ok

**Regressions:** None

**Pre-existing failures:** None

### Phase 4: Verdict
All FAIL_TO_PASS tests pass. Zero regressions. Contract fulfilled.

VERDICT: RESOLVED
RE-ENTER: none
