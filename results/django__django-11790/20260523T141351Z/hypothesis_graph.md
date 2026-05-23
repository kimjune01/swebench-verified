# Hypothesis graph: django__django-11790

## H₀: Initial observation (abduction)
The tests fail because `form.fields['username'].widget.attrs.get('maxlength')` returns None instead of the expected value (254 or 255).
- Confidence: deduction, 99%
- Evidence: Test failure at tests/auth_tests/test_forms.py:426 and :439

## H₁: Root cause identified (deduction)
The username field's maxlength HTML attribute is not being set because widget attrs are populated during field initialization, but max_length is set after initialization.

**Trace:**
1. AuthenticationForm declares username field at class level without max_length:
   - `django/contrib/auth/forms.py:168` - `username = UsernameField(widget=forms.TextInput(attrs={'autofocus': True}))`
2. When UsernameField is initialized, CharField.__init__ calls widget_attrs()
   - `django/forms/fields.py:103` - `extra_attrs = self.widget_attrs(widget)` and `widget.attrs.update(extra_attrs)`
3. CharField.widget_attrs() checks if self.max_length is not None
   - `django/forms/fields.py:233-235` - only adds maxlength if `self.max_length is not None`
4. At field declaration time, max_length is None, so widget attrs don't get maxlength
5. Later in AuthenticationForm.__init__, max_length is set:
   - `django/contrib/auth/forms.py:194` - `self.fields['username'].max_length = self.username_field.max_length or 254`
6. But widget.attrs are not updated, so maxlength remains absent

**Regression introduced in:** commit 5ceaf14686ce626404afb6a5fbd3d8286410bf13
- Previously: username field declared with `max_length=254` at class level
- After: username field declared without max_length, set dynamically in __init__
- The change broke widget attrs because they're only populated during field initialization

Confidence: deduction, 99%
Supporting evidence:
- `django/contrib/auth/forms.py:194` - sets max_length but not widget.attrs['maxlength']
- `django/forms/fields.py:103-104` - widget attrs populated during field __init__
- `django/forms/fields.py:233-235` - CharField.widget_attrs adds maxlength only if self.max_length is set
- `git show 5ceaf14686` - shows the exact change that caused the regression

## Craft gate-loop

### Iteration 1: String vs Integer type mismatch
- **Hypothesis**: Apply recon's fix by setting `widget.attrs['maxlength']` after setting `max_length`, using `str()` conversion to match CharField.widget_attrs() behavior
- **Diff**: Added widget maxlength update with `str(username.max_length)` in AuthenticationForm.__init__
- **Gate result**: FAIL - `AssertionError: '254' != 254` and `AssertionError: '255' != 255`
- **Evidence**: Tests expect integer values in `widget.attrs`, not strings
- **Trajectory**: Divergent (new error type - type mismatch)

### Iteration 2: Use integer maxlength value
- **Hypothesis**: Store maxlength as integer directly to match test expectations
- **Diff**: Changed `username.widget.attrs['maxlength'] = str(username.max_length)` to `username.widget.attrs['maxlength'] = username.max_length`
- **Gate result**: PASS - All 79 tests pass
- **Evidence**: Both FAIL_TO_PASS tests now pass:
  - `test_username_field_max_length_defaults_to_254` ✓
  - `test_username_field_max_length_matches_user_model` ✓
- **Trajectory**: Convergent (resolution)
- **Resolution**: The fix correctly sets the maxlength widget attribute when max_length is dynamically updated in __init__, addressing the root cause identified by recon

### Final fix
```python
username = self.fields['username']
username.max_length = self.username_field.max_length or 254
if not username.widget.is_hidden:
    username.widget.attrs['maxlength'] = username.max_length
if username.label is None:
    username.label = capfirst(self.username_field.verbose_name)
```

The fix also includes the hidden widget check (matching CharField.widget_attrs() behavior) and refactored to avoid repeated field access.

## Audit: django__django-11790

### Patch verification
- Patch is live in tree: `django/contrib/auth/forms.py` modified (9 insertions, 3 deletions)

### Full gate results
- Ran 79 tests in 0.136s
- Result: **OK** (all tests passed)

### FAIL_TO_PASS classification
- ✅ test_username_field_max_length_defaults_to_254 (auth_tests.test_forms.AuthenticationFormTest) — **PASS**
- ✅ test_username_field_max_length_matches_user_model (auth_tests.test_forms.AuthenticationFormTest) — **PASS**

### PASS_TO_PASS regressions
- **None** — all 79 tests passed, zero regressions detected

### Pre-existing failures (not counted)
- **None** — baseline capture showed same test suite passing on unpatched repo

### Verdict
All FAIL_TO_PASS tests now pass, and no PASS_TO_PASS tests regressed. The fix successfully addresses the root cause (maxlength widget attribute not being set when max_length is dynamically updated in __init__) without introducing any side effects.
