# Hypothesis graph: django__django-15382

## Node: H₀ (Abduction, iteration 1)

**Hypothesis**: The test fails because when a negated `Exists` expression has an empty subquery (`.none()`), the `EmptyResultSet` exception propagates through the WHERE clause compilation and causes the entire WHERE block to be eliminated, returning no results instead of matching all rows.

**Evidence**:
- Test creates: `Manager.objects.filter(~Exists(Manager.objects.none()) & Q(pk=manager.pk))`
- Expected: Should return the manager object (since `NOT EXISTS(empty)` = TRUE)
- Actual: Returns empty queryset

**Call path**:
1. WHERE node compiles children with AND connector
2. First child: `Exists(negated=True, queryset=Manager.objects.none())`
3. `Exists.as_sql()` calls `self.query.exists()` then `super().as_sql()`
4. `Subquery.as_sql()` calls `query.as_sql(compiler, connection)` which raises `EmptyResultSet` for `.none()`
5. `EmptyResultSet` propagates through `Exists.as_sql()` without being caught
6. WHERE node catches it, and with AND connector + non-negated WHERE, raises `EmptyResultSet`
7. Compiler catches and replaces with `where='0 = 1'`

**Semantics**:
- `EXISTS(empty_queryset)` should be FALSE
- `NOT EXISTS(empty_queryset)` should be TRUE
- In a WHERE clause, TRUE conditions should not filter rows

**Related fix**: Issue #33018 (dd1fa3a31b) added `empty_result_set_value` attribute to `Subquery` and handling in `Func.as_sql()`, but `Exists.as_sql()` doesn't catch `EmptyResultSet` from subquery compilation.

**Status**: Active hypothesis

## Craft: Gate Loop

### Iteration 1: Initial fix

**Diff applied:**
```python
# django/db/models/expressions.py, Exists.as_sql() method (lines 1212-1228)
def as_sql(self, compiler, connection, template=None, **extra_context):
    query = self.query.exists(using=connection.alias)
    try:
        sql, params = super().as_sql(
            compiler,
            connection,
            template=template,
            query=query,
            **extra_context,
        )
    except EmptyResultSet:
        if self.negated:
            return ('', [])
        raise
    if self.negated:
        sql = 'NOT {}'.format(sql)
    return sql, params
```

**Gate result:** ✅ PASS
- All 165 tests passed (1 skipped, 1 expected failure)
- FAIL_TO_PASS test `test_negated_empty_exists` now passes
- No regressions

**Resolution:** RESOLVED on first iteration. The recon diagnosis was correct: wrapping `super().as_sql()` in a try-except block to catch `EmptyResultSet` and returning `('', [])` for negated empty EXISTS allows the query to proceed with no restriction (TRUE condition in WHERE context), making `~Exists(Manager.objects.none()) & Q(pk=manager.pk)` correctly return the manager object.

## Audit: Final Verification

**Gate run:** Full test suite (165 tests)

### FAIL_TO_PASS
- `test_negated_empty_exists (expressions.tests.ExistsTests)`: **PASS** ✓

### PASS_TO_PASS
All 16 PASS_TO_PASS tests verified passing:
- `test_equal (expressions.tests.OrderByTests)`: ok ✓
- `test_hash (expressions.tests.OrderByTests)`: ok ✓
- `test_aggregates (expressions.tests.ReprTests)`: ok ✓
- `test_distinct_aggregates (expressions.tests.ReprTests)`: ok ✓
- `test_expressions (expressions.tests.ReprTests)`: ok ✓
- `test_filtered_aggregates (expressions.tests.ReprTests)`: ok ✓
- `test_functions (expressions.tests.ReprTests)`: ok ✓
- `test_resolve_output_field (expressions.tests.CombinedExpressionTests)`: ok ✓
- `test_deconstruct (expressions.tests.FTests)`: ok ✓
- `test_deepcopy (expressions.tests.FTests)`: ok ✓
- `test_equal (expressions.tests.FTests)`: ok ✓
- `test_hash (expressions.tests.FTests)`: ok ✓
- `test_not_equal_Value (expressions.tests.FTests)`: ok ✓
- `test_and (expressions.tests.CombinableTests)`: ok ✓
- `test_negation (expressions.tests.CombinableTests)`: ok ✓
- `test_or (expressions.tests.CombinableTests)`: ok ✓

### Regressions
**None** - zero PASS_TO_PASS tests regressed

### Pre-existing (not counted)
- `test_mixed_comparisons1 (expressions.tests.FTimeDeltaTests)`: expected failure (confirmed in base capture)

### Kill report
Not applicable - patch fully resolves the issue with no regressions.

**Final gate output:** `OK (skipped=1, expected failures=1)` — 165 tests, all passing except one pre-existing expected failure.

