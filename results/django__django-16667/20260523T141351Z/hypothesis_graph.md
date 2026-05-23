# Hypothesis graph: django__django-16667

## H₀: OverflowError not caught in SelectDateWidget.value_from_datadict

**Type**: abduction  
**Confidence**: 95% (deduction from code reading)  
**Status**: active

### Observation
Tests fail with `OverflowError: Python int too large to convert to C long` at `django/forms/widgets.py:1159` when `sys.maxsize + 1` is passed as year/month/day value.

### Root cause
`SelectDateWidget.value_from_datadict()` at line 1159 calls `datetime.date(int(y), int(m), int(d))` inside a try-except block that only catches `ValueError`, not `OverflowError`.

When user supplies integers larger than `sys.maxsize`, the `datetime.date()` constructor raises `OverflowError`, which propagates uncaught and crashes the server.

### Expected behavior
The widget should return a pseudo-ISO date string (e.g., "0-0-0") for invalid dates, which DateField.to_python() then validates and converts to a ValidationError with message "Enter a valid date."

### Supporting evidence
- `django/forms/widgets.py:1159-1161`: Only catches ValueError
  ```python
  try:
      date_value = datetime.date(int(y), int(m), int(d))
  except ValueError:
      return "%s-%s-%s" % (y or 0, m or 0, d or 0)
  ```
- Tests expect form validation error, not crash:
  - `test_form_field`: expects `is_valid() == False` and error `{"mydate": ["Enter a valid date."]}`
  - `test_value_from_datadict`: expects return value `"0-0-0"`

### Edit sites
- `django/forms/widgets.py` lines 1159-1161: Change `except ValueError:` to `except (ValueError, OverflowError):` to catch both exception types


## Craft: Gate Loop

### Iteration 1: Draft + Codex Volley

**Initial draft**: Added `OverflowError` to the existing `except ValueError:` clause to catch both exceptions.

**Codex feedback**: The proposed fix would fail the test. For `str(sys.maxsize + 1), "12", "1"`, the test expects `"0-0-0"` but the fix would return `"9223372036854775808-12-1"` because it preserves the year value. OverflowError needs separate handling to zero all components, while ValueError should continue preserving partially invalid input like `"2000-0-1"`.

**Revised fix**: Added separate `except OverflowError:` clause before `except ValueError:` to return `"0-0-0"` for overflow cases.

### Iteration 2: Gate Run

Applied fix to `django/forms/widgets.py` line 1160:
- Added `except OverflowError: return "0-0-0"` before the existing `except ValueError:` clause

**Gate result**: ✅ PASS
- All 26 tests passed
- FAIL_TO_PASS tests now passing:
  - test_form_field (forms_tests.field_tests.test_datefield.DateFieldTest.test_form_field)
  - test_value_from_datadict (forms_tests.widget_tests.test_selectdatewidget.SelectDateWidgetTest.test_value_from_datadict)

**Trajectory**: Convergent (success) — fix correctly handles OverflowError by returning `"0-0-0"` which DateField validation then rejects with "Enter a valid date."

## Audit: django__django-16667

### FAIL_TO_PASS
- test_form_field (forms_tests.field_tests.test_datefield.DateFieldTest.test_form_field): **PASS** ✅
- test_value_from_datadict (forms_tests.widget_tests.test_selectdatewidget.SelectDateWidgetTest.test_value_from_datadict): **PASS** ✅

### PASS_TO_PASS regressions
None — all 24 PASS_TO_PASS tests remain passing.

### Pre-existing failures (not counted)
None — both FAIL_TO_PASS tests were failing with ERROR on base (OverflowError), not pre-existing test suite issues.

### Gate result
All 26 tests passed. Both FAIL_TO_PASS tests now pass, zero regressions introduced.

### Patch applied
```diff
diff --git a/django/forms/widgets.py b/django/forms/widgets.py
index 842b73e95c..6f6cbca8dc 100644
--- a/django/forms/widgets.py
+++ b/django/forms/widgets.py
@@ -1157,6 +1157,8 @@ class SelectDateWidget(Widget):
             input_format = formats.sanitize_strftime_format(input_format)
             try:
                 date_value = datetime.date(int(y), int(m), int(d))
+            except OverflowError:
+                return "0-0-0"
             except ValueError:
                 # Return pseudo-ISO dates with zeros for any unselected values,
                 # e.g. '2017-0-23'.
```

VERDICT: RESOLVED
RE-ENTER: none
