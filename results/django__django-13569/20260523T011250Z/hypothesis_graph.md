# Hypothesis graph: django__django-13569

## H₀ (abduction): Test failure symptom
The test `test_aggregation_random_ordering` fails because when using `order_by('?')` with aggregation, the queryset returns duplicate rows with incorrect counts instead of properly grouped results. Expected: Peter Norvig with contact_count=2. Actual: Peter Norvig appears twice with contact_count=1.

**Evidence**: Test output shows `Counter({('Peter Norvig', 1): 2, ...})` instead of expected `Counter({..., ('Peter Norvig', 2): 1})`

## H₁ (deduction): Root cause - Random() in GROUP BY
**Status**: PROPOSED

The Random() expression is being incorrectly added to the GROUP BY clause when `order_by('?')` is used with aggregation.

**Call path**:
1. `order_by('?')` → compiler.py:310 creates `OrderBy(Random())`
2. `get_group_by()` → compiler.py:132 calls `expr.get_group_by_cols()` for all non-ref order_by expressions
3. `OrderBy.get_group_by_cols()` → expressions.py:1228-1232 delegates to source expressions
4. `Random().get_group_by_cols()` → expressions.py:349-351 returns `[self]` (base implementation)
5. Random() gets added to GROUP BY clause, breaking aggregation by creating extra groups

**Supporting evidence**:
- `django/db/models/sql/compiler.py:310` - Creates `OrderBy(Random())` for '?' ordering
- `django/db/models/sql/compiler.py:132` - Unconditionally adds `expr.get_group_by_cols()` to GROUP BY for non-ref order_by
- `django/db/models/expressions.py:1228-1232` - OrderBy delegates get_group_by_cols to wrapped expression
- `django/db/models/expressions.py:349-351` - Base Expression.get_group_by_cols returns [self] when not aggregate
- `django/db/models/functions/math.py:144` - Random class has no get_group_by_cols override

**Confidence**: deduction — 98%

## Edit sites

**Primary fix**: `django/db/models/sql/compiler.py` lines 128-133 (get_group_by method)

Current code:
```python
for expr, (sql, params, is_ref) in order_by:
    # Skip References to the select clause, as all expressions in the
    # select clause are already part of the group by.
    if not is_ref:
        expressions.extend(expr.get_group_by_cols())
```

Change needed: Filter out Random instances from the columns returned by get_group_by_cols(), since Random() is a non-deterministic function used only for ordering and should not affect grouping.

Note: Random is already imported in compiler.py line 10: `from django.db.models.functions import Cast, Random`

## /craft gate loop

### Iteration 1: Initial fix attempt (compiler-side filtering)
**Approach**: Filter out Random instances in SQLCompiler.get_group_by() loop
**codex feedback**: Fix too narrow - behavior belongs on the expression itself, not in compiler. Random should override get_group_by_cols() to return [].
**Status**: Not gated - revised based on codex feedback

### Iteration 2: Expression-level fix
**Approach**: Added get_group_by_cols(self, alias=None) method to Random class returning []
**File**: django/db/models/functions/math.py
**Change**: 
```python
class Random(NumericOutputFieldMixin, Func):
    function = 'RANDOM'
    arity = 0

    def get_group_by_cols(self, alias=None):
        return []
```
**Gate result**: ✅ PASS - All 68 tests passed, including test_aggregation_random_ordering
**Trajectory**: Convergent (success)

## /audit — Final verification

**Patch content**:
```diff
django/db/models/functions/math.py | 3 +++
 1 file changed, 3 insertions(+)

+    def get_group_by_cols(self, alias=None):
+        return []
```

### FAIL_TO_PASS results
- ✅ `test_aggregation_random_ordering`: PASS (was FAIL on base)

### PASS_TO_PASS results
All 68 tests in the suite pass. No regressions detected.

Key PASS_TO_PASS tests verified:
- test_aggregate_alias: ok
- test_aggregate_annotation: ok
- test_aggregate_in_order_by: ok
- test_aggregate_multi_join: ok
- test_aggregate_over_aggregate: ok
- test_aggregate_over_complex_annotation: ok
- test_aggregation_exists_annotation: ok
- test_aggregation_expressions: ok
- test_aggregation_order_by_not_selected_annotation_values: ok
- test_aggregation_subquery_annotation: ok
- test_aggregation_subquery_annotation_exists: ok
- (plus 57 other tests, all passing)

### Pre-existing failures
None.

### Final assessment
The fix correctly prevents Random() from being included in the GROUP BY clause by overriding `get_group_by_cols()` to return an empty list. This aligns with Random()'s semantics as a non-deterministic ordering function that should not affect result grouping.

VERDICT: RESOLVED
RE-ENTER: none
