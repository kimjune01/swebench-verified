# Hypothesis graph: django__django-14631

## H₀: Initial diagnosis (abduction → deduction)

**Mode:** Deduction (traced code path, 98% confidence)

**Symptom:**
- Test `test_datetime_clean_disabled_callable_initial_bound_field` fails: cleaned_data['dt'] has seconds=46, but bf.initial has seconds=47
- Test `test_datetime_clean_disabled_callable_initial_microseconds` fails: cleaned_data['dt'] retains microseconds (123456), but should have them stripped

**Root Cause:**
`BaseForm._clean_fields()` (django/forms/forms.py:392, 397) calls `self.get_initial_for_field(field, name)` directly instead of accessing the value through `self[name].initial` (the BoundField). This causes:

1. **Callable invoked multiple times:** The test uses a stateful callable (`FakeTime().now`) that increments seconds on each call. `_clean_fields()` calls it once (gets seconds=46), then `BoundField.initial` calls it again (gets seconds=47). Since `BoundField.initial` is a `@cached_property`, it should only be called once.

2. **Microseconds not stripped:** `BoundField.initial` (boundfield.py:216-219) strips microseconds when `widget.supports_microseconds` is False. `DateTimeInput` has `supports_microseconds = False` (widgets.py:482). But `get_initial_for_field()` doesn't strip microseconds, so cleaned_data retains them.

**Evidence:**
- boundfield.py:212: `@cached_property` decorator on `initial`
- boundfield.py:216-219: Microsecond stripping logic in BoundField.initial
- forms.py:392: `_clean_fields()` calls `get_initial_for_field()` for disabled fields
- forms.py:397: `_clean_fields()` calls `get_initial_for_field()` for FileField initial
- forms.py:444: `changed_data()` already uses `self[name].initial` (the correct approach)
- widgets.py:482: `DateTimeBaseInput.supports_microseconds = False`

**Edit Sites:**
- django/forms/forms.py:392 - Replace `self.get_initial_for_field(field, name)` with `self[name].initial`
- django/forms/forms.py:397 - Replace `self.get_initial_for_field(field, name)` with `self[name].initial`

**Rejected Hypotheses:** None yet (first diagnosis)


## Craft iteration 1

**Hypothesis:** Use `self[name].initial` instead of `self.get_initial_for_field(field, name)` to ensure callables are cached and microseconds are stripped.

**Changes applied:**
- Line 392: `value = self[name].initial` (was `self.get_initial_for_field(field, name)`)
- Line 397: `initial = self[name].initial` (was `self.get_initial_for_field(field, name)`)

**codex pre-gate feedback:** Raised concern that FileField change (line 397) is broader than the failing tests require, affecting all FileFields not just disabled ones. Noted this is a behavior change but probably desirable for consistency.

**Gate result:** ✅ PASS - All 120 tests passed
- test_datetime_clean_disabled_callable_initial_bound_field: ok
- test_datetime_clean_disabled_callable_initial_microseconds: ok

**E-value classification:** Convergent (resolved) - FAIL_TO_PASS tests now pass, no regressions.

**Resolution:** The fix ensures BoundField.initial's @cached_property is used, which:
1. Invokes callables once and caches the result
2. Strips microseconds when widget doesn't support them
Both behaviors now match what the widget renders.


## Audit: django__django-14631

### FAIL_TO_PASS
- test_datetime_clean_disabled_callable_initial_bound_field: **PASS** ✓
- test_datetime_clean_disabled_callable_initial_microseconds: **PASS** ✓

### PASS_TO_PASS regressions
None — all 120 tests passed.

### Pre-existing failures (not counted)
None

### Full gate output
```
Ran 120 tests in 0.129s
OK
```

All FAIL_TO_PASS tests now pass. Zero regressions. The craft patch correctly addresses both issues:
1. Callable initial values are now cached via BoundField.initial's @cached_property
2. Microseconds are stripped via BoundField.initial's widget-aware logic

VERDICT: RESOLVED
RE-ENTER: none
