# Hypothesis graph: django__django-15741

## H₀: Baseline (abduction)
The tests fail because `get_format()` in `django/utils/formats.py` receives a lazy string object (from `gettext_lazy()`) but calls `getattr()` with it, which requires a regular string as the attribute name.

**Evidence:**
- Stack trace shows: `TypeError: getattr(): attribute name must be string` at line 128 in `django/utils/formats.py`
- Both failing tests pass lazy strings: `gettext_lazy("DATE_FORMAT")` and `_("H:i")`
- The error occurs at `val = getattr(module, format_type, None)` where `format_type` is the lazy object

**Failure mode:** TypeError exception

## H₁: Root cause localization (deduction - 95%)
The root cause is in `django/utils/formats.py:get_format()` function. The `format_type` parameter is used directly with `getattr()` at multiple locations:
- Line 128: `val = getattr(module, format_type, None)`
- Line 134: `val = getattr(settings, format_type)`

The `getattr()` built-in function requires its second argument (the attribute name) to be a string type, not a lazy proxy object.

**Supporting evidence:**
- `/testbed/django/utils/formats.py:128` - `val = getattr(module, format_type, None)`
- `/testbed/django/utils/formats.py:134` - `val = getattr(settings, format_type)`
- Python documentation: `getattr(object, name[, default])` where `name` must be a string

## H₂: Additional cache key issue (deduction - 90%)
Line 116 creates a cache key using the raw `format_type`: `cache_key = (format_type, lang)`. If `format_type` is a lazy object, this creates a tuple with a lazy object inside, which could lead to cache misses when the same format is requested with a regular string vs. a lazy string.

**Impact:** The cache won't work properly for lazy strings, even if we fix the `getattr()` issue.


## Craft Gate Loop - Iteration 1

**Fix Applied:**
- Added `format_type = str(format_type)` at line 109 in `django/utils/formats.py`, immediately after the function docstring and before any usage of the parameter.

**Codex Review:**
- No blocking issues identified
- Placement is correct (before cache lookup, getattr(), membership checks, and cache write)
- Potential impact: only unsupported callers passing non-string, non-lazy objects would see different behavior (str(obj) instead of original object in fallback cases), which is acceptable per documented API

**Gate Result:**
```
Ran 106 tests in 0.297s

OK
```

**Status:** ✅ PASS
- Both FAIL_TO_PASS tests now passing:
  - `test_date_lazy (template_tests.filter_tests.test_date.DateTests)` 
  - `test_get_format_lazy_format (i18n.tests.FormattingTests)`
- No regressions observed

---

# Audit: django__django-15741

## FAIL_TO_PASS
- test_date_lazy (template_tests.filter_tests.test_date.DateTests): **PASS** ✓
- test_get_format_lazy_format (i18n.tests.FormattingTests): **PASS** ✓

## PASS_TO_PASS regressions
None — all 106 tests passed in the gate.

## Pre-existing (not counted, confirmed against base capture)
None — no failures in the gate output.

## Verdict Summary
The patch successfully resolves the issue:
- Both FAIL_TO_PASS tests now pass
- Zero PASS_TO_PASS regressions
- Full gate: 106 tests in 0.298s, OK

The single-line fix (`format_type = str(format_type)`) at line 109 in `django/utils/formats.py` correctly handles lazy string objects before they're used with `getattr()` and in the cache key construction.

VERDICT: RESOLVED
RE-ENTER: none
