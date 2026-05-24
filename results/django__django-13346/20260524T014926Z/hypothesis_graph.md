# Hypothesis graph: django__django-13346

## H₁: Missing KeyTransformIn lookup (abduction, 85%)

**Observation**: All 9 subtests in `test_key_in` fail with empty QuerySets on SQLite. The tests expect `value__foo__in=['bar']` to return matching objects, but it returns nothing.

**Root cause**: No `KeyTransformIn` lookup class exists. When `__in` is used on a JSON key transform, Django falls back to the default `In` lookup from `django.db.models.lookups`, which doesn't wrap RHS values with necessary JSON extraction functions for MySQL, Oracle, and SQLite.

**Evidence**:
- `django/db/models/fields/json.py:482-496` - Shows registered lookups on `KeyTransform`. No `In` lookup registered.
- `django/db/models/fields/json.py:380-406` - `KeyTransformExact.process_rhs()` shows the pattern: Oracle needs `JSON_QUERY`/`JSON_VALUE`, SQLite needs `JSON_EXTRACT(%s, '$')`
- `django/db/models/fields/json.py:240-254` - `JSONExact.process_rhs()` shows MySQL needs `JSON_EXTRACT(%s, '$')`
- `django/db/models/fields/json.py:473-478` - `KeyTransformNumericLookupMixin` shows the mixin pattern for extending lookups

**Edit sites**:
1. `django/db/models/fields/json.py` lines 470-480: Add `KeyTransformIn` class with `process_rhs` override
2. `django/db/models/fields/json.py` line 492: Register `KeyTransformIn` on `KeyTransform` (between `KeyTransformIRegex` and numeric lookups)

**Confidence**: 85% (abduction) - Direct code reading shows the missing lookup class, and the pattern from existing lookups (`KeyTransformExact`, `KeyTransformNumericLookupMixin`) is clear.

## Craft iteration 1 - RESOLVED

**Action**: Implemented `KeyTransformIn` lookup class

**Implementation**:
- Added `KeyTransformIn(lookups.In)` class in `django/db/models/fields/json.py` after `KeyTransformIRegex` (line 458)
- Overrode `resolve_expression_parameter()` to wrap RHS values with database-specific JSON extraction functions
- MySQL/SQLite: `JSON_EXTRACT(%s, '$')`
- Oracle: `JSON_QUERY(JSON_OBJECT('value' VALUE %s FORMAT JSON), '$.value')` for lists/dicts, `JSON_VALUE(...)` for scalars
- Only applies wrapping when `not connection.features.has_native_json_field` (excludes PostgreSQL which has native JSON support)
- Registered `KeyTransformIn` with `KeyTransform.register_lookup()` (line 514)

**Codex feedback incorporated**:
- Used `resolve_expression_parameter()` instead of `process_rhs()` or `batch_process_rhs()` to preserve compiled SQL and handle expressions correctly
- Oracle: Used `JSON_OBJECT('value' VALUE %s FORMAT JSON)` wrapper to avoid SQL injection and properly format bind parameters
- Checked `hasattr(param, 'as_sql')` to avoid wrapping expression objects

**Gate result**: ✅ PASS
- `test_key_in`: ✅ ok
- `test_key_iregex`: ✅ ok  
- All 75 tests passed (8 skipped)

**E-value trajectory**: Convergent success - first attempt resolved the issue

**Confidence**: 100% - gate confirms both FAIL_TO_PASS tests pass

---

## Audit: django__django-13346

### Patch verification

**Patch status**: Live (22 lines added to `django/db/models/fields/json.py`)

### FAIL_TO_PASS results

- `test_key_in (model_fields.test_jsonfield.TestQuerying)`: **PASS** ✅
- `test_key_iregex (model_fields.test_jsonfield.TestQuerying)`: **PASS** ✅

### PASS_TO_PASS regressions

**None** - All 75 tests passed (8 skipped)

### Pre-existing failures (not counted, confirmed against base capture)

**None** - The baseline showed 9 failures, all have been resolved by the patch

### Gate summary

```
Ran 75 tests in 0.066s
OK (skipped=8)
```

**Full contract satisfied**:
- ✅ All FAIL_TO_PASS tests now pass
- ✅ Zero PASS_TO_PASS regressions
- ✅ No new failures introduced
