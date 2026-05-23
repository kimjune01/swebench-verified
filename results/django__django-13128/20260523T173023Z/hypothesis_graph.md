# Hypothesis graph: django__django-13128

## H₀ — Initial Hypothesis (Abduction)

**Created:** 2026-05-23 (recon iteration 1)

**Claim:** Temporal subtraction (DateField - DateField, etc.) fails because output_field resolution happens too late in the expression lifecycle.

**Evidence:**
- Tests fail with `TypeError: expected string or bytes-like object` when database tries to parse duration results as datetime/date/time strings
- `CombinedExpression.as_sql()` line 462-464 has logic to detect temporal subtraction and delegate to `TemporalSubtraction`
- `TemporalSubtraction` has correct `output_field = fields.DurationField()` class attribute
- But `CombinedExpression.resolve_expression()` lines 475-482 doesn't check for temporal subtraction, so expression remains as `CombinedExpression` with wrong output_field until SQL generation

**Reasoning mode:** Deduction (traced code path from failing test through expression resolution and SQL compilation)

**Confidence:** 98%

**Proposed fix:** Move temporal subtraction detection from `CombinedExpression.as_sql()` to `CombinedExpression.resolve_expression()`. After resolving lhs and rhs, check if connector is SUB and both sides are the same temporal type, then return a `TemporalSubtraction` instance instead of `CombinedExpression`.

**Edit location:** `django/db/models/expressions.py` lines 475-482 (CombinedExpression.resolve_expression method)


---

## Craft gate-loop nodes

### Iteration 1: Initial fix attempt
**Applied patch:**
- Modified `CombinedExpression.resolve_expression()` to detect temporal subtraction and return `TemporalSubtraction` instance
- Preserved `is_summary` state as recommended by codex
- Added guard against double-wrapping `TemporalSubtraction`

**Gate result:** **REGRESSION**
- 2 errors: `test_annotation_with_outerref`, `test_outerref_with_operator`
- Error: `AttributeError: 'ResolvedOuterRef' object has no attribute 'output_field'`
- Root cause: Only catching `FieldError`, not `AttributeError`

**Trajectory:** Divergent (new error introduced)

### Iteration 2: Fix exception handling
**Applied patch:**
- Changed `except FieldError:` to `except (FieldError, AttributeError):`
- This handles expressions that lack `output_field` attribute entirely (like `ResolvedOuterRef`)

**Gate result:** **GREEN**
- All 143 tests passed (2 skipped)
- All FAIL_TO_PASS tests now pass:
  - `test_date_case_subtraction`
  - `test_date_subquery_subtraction`
  - `test_date_subtraction`
  - `test_datetime_subquery_subtraction`
  - `test_datetime_subtraction_microseconds`
  - `test_time_subquery_subtraction`
  - `test_time_subtraction`
- No PASS_TO_PASS regressions

**Trajectory:** Convergent (resolved)

## Resolution

The fix successfully makes temporal subtraction (DateField - DateField, DateTimeField - DateTimeField, TimeField - TimeField) work without requiring ExpressionWrapper by detecting the pattern early in `resolve_expression()` and converting to `TemporalSubtraction` before `output_field` is resolved.

**Final patch:**
```python
def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
    c = self.copy()
    c.is_summary = summarize
    c.lhs = c.lhs.resolve_expression(query, allow_joins, reuse, summarize, for_save)
    c.rhs = c.rhs.resolve_expression(query, allow_joins, reuse, summarize, for_save)
    # Detect temporal subtraction and convert to TemporalSubtraction
    try:
        lhs_type = c.lhs.output_field.get_internal_type()
        rhs_type = c.rhs.output_field.get_internal_type()
    except (FieldError, AttributeError):
        pass
    else:
        datetime_fields = {'DateField', 'DateTimeField', 'TimeField'}
        if (c.connector == c.SUB and lhs_type in datetime_fields and
            lhs_type == rhs_type and not isinstance(c, TemporalSubtraction)):
            temporal = TemporalSubtraction(c.lhs, c.rhs)
            temporal.is_summary = summarize
            return temporal
    return c
```

---

# Audit: django__django-13128

**Run timestamp:** 2026-05-23

## FAIL_TO_PASS
- test_date_case_subtraction (expressions.tests.FTimeDeltaTests): **PASS** ✓
- test_date_subquery_subtraction (expressions.tests.FTimeDeltaTests): **PASS** ✓
- test_date_subtraction (expressions.tests.FTimeDeltaTests): **PASS** ✓
- test_datetime_subquery_subtraction (expressions.tests.FTimeDeltaTests): **PASS** ✓
- test_datetime_subtraction_microseconds (expressions.tests.FTimeDeltaTests): **PASS** ✓
- test_time_subquery_subtraction (expressions.tests.FTimeDeltaTests): **PASS** ✓
- test_time_subtraction (expressions.tests.FTimeDeltaTests): **PASS** ✓

## PASS_TO_PASS regressions
none

## Pre-existing (not counted, confirmed against base capture)
none

## Summary
All 143 tests passed (2 skipped). The patch successfully resolves temporal subtraction by detecting the pattern in `resolve_expression()` and converting to `TemporalSubtraction` before output_field resolution. The fix handles both standard field expressions and edge cases like `ResolvedOuterRef` via the dual exception catch.

VERDICT: RESOLVED
RE-ENTER: none
