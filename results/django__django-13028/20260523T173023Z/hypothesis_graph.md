# Hypothesis graph: django__django-13028

## H₀ (abduction, 85%)

**Symptom**: Tests fail with `NotSupportedError: ExtraInfo is disallowed in the filter clause`

**Root cause**: `check_filterable` (query.py:1127) uses `getattr(expression, 'filterable', True)` without verifying the object is a SQL expression. When passed a model instance with a `filterable` database field set to `False`, it incorrectly raises NotSupportedError.

**Evidence**:
- `django/db/models/sql/query.py:1127`: `if not getattr(expression, 'filterable', True):`
- `django/db/models/expressions.py:138`: `BaseExpression` has class attribute `filterable = True`
- `django/db/models/expressions.py:1063`: `Window` expression overrides with `filterable = False`
- `tests/queries/models.py:45`: `ExtraInfo` model has field `filterable = models.BooleanField(default=True)`
- Test creates instance with `filterable=False`, triggering the bug

**Design intent**: 
- `filterable` is a class attribute on SQL expressions to indicate if they can be used in WHERE clauses
- Window expressions have `filterable=False` (SQL standard disallows them in WHERE)
- `check_filterable` should only check this on `BaseExpression` instances, not arbitrary objects

**Call path**:
1. `Author.objects.filter(extra=self.e2)` where `e2.filterable == False`
2. `build_filter` (query.py:1269) calls `check_filterable(value)` on the model instance
3. `check_filterable` picks up the database field value instead of checking for SQL expression metadata

**Edit site**: `django/db/models/sql/query.py` lines 1125-1135

## Craft: Gate Loop Iteration 1

**Drafted fix:** Modified `check_filterable` in `django/db/models/sql/query.py` to only check the `filterable` attribute on `BaseExpression` instances, not arbitrary objects.

**Codex pre-gate review:** Approved logic, requested line wrapping for Django style compliance.

**Applied change:**
```python
# Lines 1125-1131 of django/db/models/sql/query.py
def check_filterable(self, expression):
    """Raise an error if expression cannot be used in a WHERE clause."""
    if (
        isinstance(expression, BaseExpression) and
        not getattr(expression, 'filterable', True)
    ):
        raise NotSupportedError(
            expression.__class__.__name__ + ' is disallowed in the filter '
            'clause.'
        )
```

**Gate result:** ✅ PASS
- `test_field_with_filterable` (queries.tests.Queries1Tests): ok
- `test_ticket8439` (queries.tests.Queries1Tests): ok
- Ran 2 tests in 0.028s: OK

**Regression check:**
- Window expression rejection still works: `expressions_window.tests.NonQueryWindowTests.test_invalid_filter` passes
- Full queries test suite: 387 tests, OK (skipped=13, expected failures=2)

**Trajectory:** Convergent-resolved. FAIL_TO_PASS tests pass, no regressions.

**Root cause confirmed:** The `check_filterable` method was checking the `filterable` attribute on any object without type discrimination. When a model instance with a `filterable` database field was passed as a filter value, it incorrectly read the field value instead of checking for SQL expression metadata.

**Fix verified:** Adding `isinstance(expression, BaseExpression)` check ensures only SQL expressions are checked for the `filterable` attribute, allowing model instances with `filterable` fields to pass through correctly while still preventing Window expressions from being used in WHERE clauses.

## Audit: django__django-13028

### Patch Status
Patch is live in the container:
- File: `django/db/models/sql/query.py`
- Change: Added `isinstance(expression, BaseExpression)` check to `check_filterable` method (lines 1127-1132)

### FAIL_TO_PASS Results
- `test_field_with_filterable` (queries.tests.Queries1Tests): **PASS** ✅
- `test_ticket8439` (queries.tests.Queries1Tests): **PASS** ✅

### PASS_TO_PASS Regressions
**None** - Full queries test suite passes:
- 387 tests OK (skipped=13, expected failures=2)
- No new failures introduced

### Pre-existing Failures
**None** - All tests in the queries test suite that were passing on base continue to pass.

### Regression Verification
Verified Window expression filtering still works correctly:
- `expressions_window.tests.NonQueryWindowTests.test_invalid_filter`: **PASS** ✅
- This confirms Window expressions with `filterable=False` are still correctly rejected in WHERE clauses

### Analysis
The fix correctly addresses the root cause:
1. **Problem**: `check_filterable` was checking the `filterable` attribute on any object, including model instances with a `filterable` database field
2. **Solution**: Added `isinstance(expression, BaseExpression)` guard to only check SQL expressions
3. **Effect**: Model instances with `filterable` fields now pass through correctly, while Window expressions are still properly rejected

### Conclusion
All FAIL_TO_PASS tests pass, zero PASS_TO_PASS regressions detected. The fix is minimal, targeted, and preserves existing behavior for Window expressions.

VERDICT: RESOLVED
RE-ENTER: none
