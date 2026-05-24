# Hypothesis graph: django__django-15375

## Hypothesis H₀: Coalesce wrapper missing is_summary flag (Abduction, 98%)

**Status:** Active (first diagnosis)

**Symptom:** `SELECT FROM (...)` – outer SELECT clause is empty when using `aggregate(Sum(..., default=0))` after `annotate()`

**Root cause:** 
`Aggregate.resolve_expression` (aggregates.py:69) wraps the aggregate in `Coalesce` when a `default` is provided, but creates the Coalesce directly without resolving it. The Coalesce gets `is_summary=False` (default) even though the wrapped aggregate has `is_summary=True`. 

In `Query.get_aggregation` (query.py:476), the code checks `if expression.is_summary` to move summary annotations to the outer query. Since Coalesce has `is_summary=False`, it's not moved, leaving the outer query with no annotations.

**Evidence:**
- aggregates.py:69: `return Coalesce(c, default, ...)` creates Coalesce without resolving
- query.py:476: `if expression.is_summary:` checks Coalesce's flag, not inner aggregate
- compiler.py:1675-1677: Outer SELECT built from empty `annotation_select`

**Proposed fix:**
After creating Coalesce at aggregates.py:69, copy `is_summary` from the wrapped aggregate `c` to the Coalesce.

**Reasoning mode:** Deduction (traced code path, no external state needed)

## Craft Phase - Implementation

### Gate Iteration 1 (RESOLVED)

**Hypothesis**: The `is_summary` flag is not preserved when wrapping an aggregate with `Coalesce` in the `resolve_expression` method of the `Aggregate` class.

**Edit Site**: `django/db/models/aggregates.py:68`

**Change Applied**:
```python
# Before:
return Coalesce(c, default, output_field=c._output_field_or_none)

# After:
coalesced = Coalesce(c, default, output_field=c._output_field_or_none)
coalesced.is_summary = c.is_summary
return coalesced
```

**Gate Result**: ✅ PASS
- All 96 tests passed
- `test_aggregation_default_after_annotation` now passes
- No regressions detected

**Root Cause Confirmed**: When an aggregate has a `default` parameter, Django wraps it in a `Coalesce` function. The original code at line 68 created the Coalesce wrapper but didn't preserve the `is_summary` flag from the resolved aggregate `c`. This caused the query builder to treat the Coalesce-wrapped aggregate as a non-summary expression, leaving it in the inner query instead of moving it to the outer aggregate query, resulting in an empty outer SELECT clause.

**Resolution**: The fix explicitly copies the `is_summary` attribute from the resolved aggregate to the Coalesce wrapper before returning it. This ensures the query builder correctly recognizes the Coalesce-wrapped aggregate as a summary expression and places it in the outer query.

---

# Audit: django__django-15375

## FAIL_TO_PASS
- test_aggregation_default_after_annotation (aggregation.tests.AggregateTestCase): **PASS** ✅

## PASS_TO_PASS regressions
None - all 96 tests in the suite passed.

## Pre-existing (not counted, confirmed against base capture)
None - the base capture showed all tests except the FAIL_TO_PASS test were passing, and they remain passing.

## Verification

**Patch confirmed live:**
```
 django/db/models/aggregates.py | 4 +++-
 1 file changed, 3 insertions(+), 1 deletion(-)
```

**Full gate output:** All 96 tests in aggregation.tests.AggregateTestCase passed in 0.109s.

**Contract satisfied:**
- ✅ All FAIL_TO_PASS tests now pass (1/1)
- ✅ Zero PASS_TO_PASS regressions (0 failures in 95 tests)
- ✅ No new failures introduced

The fix successfully preserves the `is_summary` flag when wrapping aggregates in `Coalesce`, allowing the query builder to correctly place the expression in the outer aggregate query instead of leaving it in the inner query with an empty SELECT clause.

VERDICT: RESOLVED
RE-ENTER: none
