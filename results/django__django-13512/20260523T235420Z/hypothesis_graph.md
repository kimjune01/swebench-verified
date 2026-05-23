# Hypothesis graph: django__django-13512

## H₀: Initial diagnosis (abduction → deduction)
**Symptom**: Tests fail because Unicode characters in JSONField values are being ASCII-escaped (`你好`) instead of preserved as actual Unicode characters (`你好`).

**Root cause identified through code trace**:
The `json.dumps()` function is called without `ensure_ascii=False` parameter. Python's `json.dumps()` defaults to `ensure_ascii=True`, which escapes all non-ASCII characters as `\uXXXX` sequences.

**Call path for test_json_display_for_field**:
1. Test → `display_for_field(value={'a': '你好 世界'}, field=models.JSONField())`
2. `django/contrib/admin/utils.py:401` → `field.get_prep_value(value)`
3. `django/db/models/fields/json.py:84` → `json.dumps(value, cls=self.encoder)` ← Missing `ensure_ascii=False`

**Call path for test_prepare_value**:
1. Test → `field.prepare_value('你好，世界')` where `field = forms.JSONField()`
2. `django/forms/fields.py:1261` → `json.dumps(value, cls=self.encoder)` ← Missing `ensure_ascii=False`

**Confidence**: Deduction, 99% - Traced from test to root cause through code reading.

**Edit sites enumerated**:
1. `django/db/models/fields/json.py:84` - Add `ensure_ascii=False` to `json.dumps()` in `get_prep_value()`
2. `django/db/models/fields/json.py:95` - Add `ensure_ascii=False` to `json.dumps()` in `validate()` (consistency)
3. `django/forms/fields.py:1261` - Add `ensure_ascii=False` to `json.dumps()` in `prepare_value()`
4. `django/forms/fields.py:1269-1270` - Add `ensure_ascii=False` to `json.dumps()` in `has_changed()` (consistency)

## Craft Gate Loop

### Iteration 1: Minimal fix - ensure_ascii=False

**Hypothesis**: Add `ensure_ascii=False` to `json.dumps()` calls in:
1. `django/db/models/fields/json.py:84` - `get_prep_value()`
2. `django/forms/fields.py:1261` - `prepare_value()`

**Codex volley**: Initial draft included validate() and has_changed() changes. Codex flagged:
- validate() change unnecessary (doesn't affect TypeError detection)
- has_changed() change unnecessary (both sides use same flag, so no behavioral impact)
- get_prep_value() might affect database layer (MySQL utf8mb4 concerns)

Revised to minimal: only the two methods directly used by failing tests.

**Applied diff**:
```diff
--- a/django/db/models/fields/json.py
+++ b/django/db/models/fields/json.py
@@ -81,7 +81,7 @@ class JSONField(CheckFieldDefaultMixin, Field):
     def get_prep_value(self, value):
         if value is None:
             return value
-        return json.dumps(value, cls=self.encoder)
+        return json.dumps(value, ensure_ascii=False, cls=self.encoder)

--- a/django/forms/fields.py
+++ b/django/forms/fields.py
@@ -1258,7 +1258,7 @@ class JSONField(CharField):
     def prepare_value(self, value):
         if isinstance(value, InvalidJSONInput):
             return value
-        return json.dumps(value, cls=self.encoder)
+        return json.dumps(value, ensure_ascii=False, cls=self.encoder)
```

**Gate result**: ✅ **PASS** - All 35 tests passed
- test_json_display_for_field ✅
- test_label_for_field ✅
- test_prepare_value ✅

**Resolution**: The minimal fix of adding `ensure_ascii=False` to the two json.dumps() calls directly used by the failing tests resolves all FAIL_TO_PASS tests without breaking any PASS_TO_PASS tests.

## Audit: django__django-13512

### FAIL_TO_PASS (3 tests - all must pass)
1. `test_prepare_value (forms_tests.field_tests.test_jsonfield.JSONFieldTest)` - **PASS** ✓
2. `test_json_display_for_field (admin_utils.tests.UtilsTests)` - **PASS** ✓  
3. `test_label_for_field (admin_utils.tests.UtilsTests)` - **PASS** ✓

### PASS_TO_PASS regressions
**None** - All 35 tests in the suite passed.

### Pre-existing failures (confirmed against base capture)
**None** - No failures detected in gate run.

### Verdict
The patch successfully resolves all three FAIL_TO_PASS tests by adding `ensure_ascii=False` to `json.dumps()` calls in:
- `django/db/models/fields/json.py:84` (get_prep_value)
- `django/forms/fields.py:1261` (prepare_value)

This prevents Unicode characters from being escaped as `\uXXXX` sequences, preserving them as actual Unicode in JSON output. Zero regressions introduced.

