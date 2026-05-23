# Hypothesis graph: django__django-14351

## Node: H₁ - Initial Recon (2026-05-23)

**Type:** Abduction
**Confidence:** 90%

**Hypothesis:** The `In` and `RelatedIn` lookup classes check `getattr(self.rhs, 'has_select_fields', True)` to determine if they should clear the select clause and add only the pk field for subqueries. However, `has_select_fields` is a property on the `Query` class, not the `QuerySet` class. When `self.rhs` is a QuerySet (which is the common case), the `getattr` returns the default value `True`, causing the condition `not True` to be False, so the select clause is NOT cleared. This results in the subquery selecting all default columns instead of just the primary key, causing the "subquery must return only one column" error.

**Evidence:**
- `django/db/models/lookups.py:404` - `In.process_rhs` checks `if not getattr(self.rhs, 'has_select_fields', True)`
- `django/db/models/fields/related_lookups.py:89` - `RelatedIn.as_sql` checks `if (not getattr(self.rhs, 'has_select_fields', True) and ...)`
- `django/db/models/sql/query.py:244-245` - `has_select_fields` is a `@property` on Query, not QuerySet
- `django/db/models/query.py:1379-1387` - QuerySet does NOT have `has_select_fields` attribute
- Test output: "sub-select returns 3 columns - expected 1" - the Author model has 3 fields (id, name, age)

**Root Cause:**
The lookups assume `self.rhs` is a Query object and directly access `has_select_fields`, but `self.rhs` is actually a QuerySet. Since QuerySet doesn't have this attribute, `getattr` returns the default True, preventing the select clause from being cleared.

**Edit Sites:**
1. `django/db/models/lookups.py` lines 404-406 - In.process_rhs: Change to check `self.rhs.query.has_select_fields` when `self.rhs` is a QuerySet
2. `django/db/models/fields/related_lookups.py` lines 89-101 - RelatedIn.as_sql: Change to check `self.rhs.query.has_select_fields` when `self.rhs` is a QuerySet

**Fix Strategy:**
Check if `self.rhs` is a QuerySet, and if so, access the `query` attribute to get the Query object before checking `has_select_fields`. This ensures we check the actual Query's state rather than getting the default True value from `getattr`.


## Craft iteration: Gate loop (iterations 1-4)

**Recon diagnosis confirmed**: The error "sub-select returns 3 columns - expected 1" matches exactly what recon identified - `has_select_fields` property exists on Query but not QuerySet, causing `getattr(self.rhs, 'has_select_fields', True)` to return True (default) when self.rhs is a QuerySet, preventing the optimization that clears select and adds only pk.

**Implementation attempts**:
1. Tried `getattr(getattr(self.rhs, 'query', self.rhs), 'has_select_fields', True)` - failed because this modifies a temp variable, not self.rhs which is later used by Lookup.process_rhs
2. Tried assigning Query back to self.rhs: `self.rhs = self.rhs.query` - still failing
3. Added field existence check for M2M intermediate tables (discovered self.lhs.field is ForeignKey in M2M intermediate table, not ManyToManyField directly)
4. Applied isinstance(Query) checks like Exact lookup does

**Evidence from debug**:
- RelatedIn.as_sql is called with isinstance(MultiColSource)=False 
- The else branch runs and attempts to optimize
- Debug showed `has_select_fields=False, target_is_pk=True` - optimization should run
- Field `id` exists on Author model and optimization runs (confirmed by debug)
- But test still fails with 3-column subquery

**Hypothesis**: The optimization code runs in RelatedIn.as_sql and modifies self.rhs (now Query), but somewhere downstream the original QuerySet is being used again, or the Query object is being re-evaluated and losing the select clause optimization. The flow through Lookup.process_rhs -> compiler.compile(self.rhs) may be creating a fresh SQL generation that doesn't respect the modified select clause.

**Status**: Convergent-stuck after 4 iterations. Recon diagnosis is correct, but implementation approach may need different intervention point (possibly in query compilation rather than lookup processing).


## Final diagnosis (iteration 4+)

**Discovery**: `self.rhs` in `In.process_rhs` is NOT always a QuerySet. Debug shows it's most commonly `str` or `list` (direct values), with only 3 calls where `type(self.rhs)=Query` near the end of test execution. The failing subquery likely happens in one of those 3 Query calls.

**Hypothesis revision needed**: Recon assumed the pattern was "QuerySet → check has_select_fields → get default True". But the actual flow is more complex - QuerySet gets resolved to Query via `resolve_expression`, and by the time `process_rhs` is called, `self.rhs` is already a Query object (not QuerySet). The property should work correctly on Query objects.

**The real question**: Why does `has_select_fields` return True for the Query object when it should return False for a fresh query? Or why isn't the optimization running even when has_select_fields=False?

**Evidence points to**: Either (1) the Query object already has select fields set by the time it reaches process_rhs, or (2) the optimization runs but gets undone/ignored during SQL compilation, or (3) a different code path (possibly RelatedIn with MultiColSource or a different condition branch) is generating the failing SQL.


## H2: Incorrect condition in RelatedIn.as_sql skips select clause clearing for primary key targets

**Root cause**: In `django/db/models/fields/related_lookups.py:93-94`, the condition checking whether to clear and limit the subquery select clause has two parts:
```python
if (not getattr(self.rhs, 'has_select_fields', True) and
        not getattr(self.lhs.field.target_field, 'primary_key', False)):
```

This requires BOTH:
1. The Query has no explicit select fields (`has_select_fields` = False)
2. The target field is NOT a primary key

For `Q(authors__in=authors)` where `authors` is a ManyToManyField:
- Condition 1 is True (Query has `select=[]`, so `has_select_fields` returns False)
- Condition 2 is False (Author's implicit `id` field has `primary_key=True`)
- Result: `True AND False = False` → block doesn't execute

The problem: When the block doesn't execute, the Query still has `default_cols=True`, which causes the compiler to select ALL columns (id, name, age) instead of just the primary key, triggering "sub-select returns 3 columns - expected 1".

**Edit site**: `django/db/models/fields/related_lookups.py:93-94`
- Remove the second condition `and not getattr(self.lhs.field.target_field, 'primary_key', False)`
- Keep just: `if not getattr(self.rhs, 'has_select_fields', True):`

**Evidence**:
- `django/db/models/sql/query.py:244` - `has_select_fields` only checks `select`, `annotation_select_mask`, `extra_select_mask` (not `default_cols`)
- `django/db/models/sql/query.py:164` - `default_cols` initialized to True
- `django/db/models/sql/compiler.py:228` - If `default_cols=True`, calls `get_default_columns()` which selects all fields
- `git blame` shows condition added in d66378a8b2d for #28175 (parent model FK lookups)

**Confidence**: Deduction - 95% (traced code path, identified exact conditional logic error)


## Craft Gate Loop - Iteration Summary

### Iteration 1: Apply recon diagnosis (remove primary_key condition)
- Changed condition from `if (not getattr(self.rhs, 'has_select_fields', True) and not getattr(self.lhs.field.target_field, 'primary_key', False)):` to `if not getattr(self.rhs, 'has_select_fields', True):`
- **Result**: FAIL - same error "sub-select returns 3 columns - expected 1"
- **Evidence**: Debug shows `has_select_fields=False`, `default_cols=True`, and `clear_select_clause()` + `add_fields()` ARE being called, but SQL still has 3 columns

### Iteration 2: Replace with set_values() per codex advice
- codex identified that `clear_select_clause()` + `add_fields()` don't fully clean Query state
- Replaced with `self.rhs.set_values([target_field])` as suggested by Django ticket #33975
- **Result**: FAIL - same error "sub-select returns 3 columns - expected 1"
- **Trajectory**: Convergent-stuck (same error persists after 3 attempts)

### Hypothesis Assessment

After 3 iterations, the fix in `RelatedIn.as_sql()` (else branch, lines 89-98) does NOT resolve the issue, despite:
1. The condition now correctly enters the if block (`has_select_fields=False`)
2. The Query modification methods are being called
3. Using both `clear_select_clause()` + `add_fields()` AND `set_values()`

**Conclusion**: The diagnosis appears incomplete or the actual code path generating the failing SQL is different from what recon identified. The `RelatedIn.as_sql()` else branch may not be the location where the subquery for the HAVING clause is being processed.

**Next**: Re-diagnose to find the actual code path that generates the subquery in the HAVING clause context.


## H3: Query cloning in resolve_expression() bypasses lookup modifications (2026-05-23)

**Type:** Abduction
**Confidence:** 75%

**Hypothesis:** The issue is not in `RelatedIn.as_sql()` or `In.process_rhs()` where previous fixes were attempted. The root cause is that when a QuerySet is used in a filter, it's converted to a Query via `resolve_expression()` which **clones** the Query (query.py:1034). The cloned Query has `default_cols=True` by default. Later lookup modifications that call `clear_select_clause()` or `set_values()` should set `default_cols=False`, but something prevents this from taking effect. The SQL compiler's `get_select()` (compiler.py:227) checks `if self.query.default_cols:` and calls `get_default_columns()` if True, which selects ALL concrete fields.

**Evidence:**
- `django/db/models/sql/query.py:1034` - `clone = self.clone()` in `resolve_expression()`
- `django/db/models/query.py:1384` - `QuerySet.resolve_expression()` calls `self.query.resolve_expression()`
- `django/db/models/sql/query.py:1073` - `resolve_lookup_value()` calls `value.resolve_expression()`
- `django/db/models/sql/compiler.py:227-228` - `if self.query.default_cols: cols = self.get_default_columns()`
- Audit kill: Prior fix in `RelatedIn.as_sql()` didn't work despite debug showing methods were called
- Test error: "sub-select returns 3 columns - expected 1" = Author's 3 fields (id, name, age)

**Root Cause:**
Query cloning happens in `resolve_expression()` before lookup processing. The clone inherits `default_cols=True`. Lookup modifications happen later but don't persist or are ignored because the compiler regenerates select from `default_cols`.

**Edit Sites (competing options):**
1. `django/db/models/sql/query.py:1033-1056` - Set `clone.default_cols = False` after cloning in `resolve_expression()` when used as subquery
2. `django/db/models/query.py:1379-1387` - Call `query.set_values(['pk'])` in `QuerySet.resolve_expression()` after cloning
3. `django/db/models/sql/query.py:1071-1088` - Modify `resolve_lookup_value()` to set select clause for Query objects

**Rejected from H₁/H₂:**
- Modifying `RelatedIn.as_sql()` - tried `set_values()`, `clear_select_clause()`, `add_fields()`, all failed
- Changing condition in `RelatedIn.as_sql()` line 93 - didn't resolve issue

**Open Questions:**
- Why don't lookup modifications persist if they're on the same Query object?
- Is there a second clone happening between lookup modification and compilation?
- Does GROUP BY/HAVING processing regenerate select clause?

## Craft Iteration - CONVERGENT STUCK

**Attempts**:
1. Modified `set_values()` to always set `default_cols=False` (not just when extra/annotations present)
2. Tried setting `default_cols=False` in `resolve_expression()` - created empty SELECT syntax error
3. Moved `set_values()` call from `SubqueryConstraint.as_sql()` to `__init__()` per codex suggestion
4. All FAIL_TO_PASS attempts result in same error: "sub-select returns 3 columns - expected 1"

**Debug Evidence**:
- `set_values()` IS being called with correct fields (`['id']`)
- Query object ID shows `set_values()` called on one object, but SQL compiled from different object
- Test involves `annotate(Count('authors'))` + HAVING clause, not simple WHERE subquery

**Hypothesis Wrong**:  
The recon diagnosis targeted standard WHERE clause subqueries via `RelatedIn.as_sql()` and `SubqueryConstraint`. But `test_having_subquery_select` uses aggregations with HAVING clauses, which may resolve queries through a different compilation path that either:
- Clones the query multiple times, causing `set_values()` to modify a different instance than the one compiled
- Resolves and caches the SELECT clause before `set_values()` is called
- Uses a separate HAVING-specific code path that bypasses the lookup modifications entirely

The fix location is not where recon identified. Need to investigate HAVING clause query compilation path.


## Audit: django__django-14351 (2026-05-23)

### FAIL_TO_PASS
- test_having_subquery_select (aggregation_regress.tests.AggregationTests): **FAIL** 
  - Error: `sqlite3.OperationalError: sub-select returns 3 columns - expected 1`
  - The subquery still returns all Author fields (id, name, age) instead of just the pk

### PASS_TO_PASS regressions
None - all PASS_TO_PASS tests passed successfully.

### Pre-existing (not counted, confirmed against base capture)
- 5 tests skipped (same as baseline): aggregate_duplicate_columns, aggregate_duplicate_columns_only, aggregate_duplicate_columns_select_related, aggregate_unmanaged_model_as_tables, aggregate_unmanaged_model_columns

### Kill report

**FAIL_TO_PASS ineffective** - The fix did not resolve the target test.

**Test**: test_having_subquery_select (aggregation_regress.tests.AggregationTests)

**Error**: `sqlite3.OperationalError: sub-select returns 3 columns - expected 1`

**Analysis**: Despite multiple craft iterations attempting fixes at different locations (In.process_rhs, RelatedIn.as_sql, Query.resolve_expression, Query.set_values), the subquery in the HAVING clause still selects all 3 Author columns instead of just the primary key.

**Code path implicated**: The test uses `annotate(Count('authors')).filter(Exists(Subquery(...)))` with a HAVING clause context. The hypothesis graph shows convergent-stuck behavior across 4+ iterations. The note at the end of the graph is critical: "test_having_subquery_select uses aggregations with HAVING clauses, which may resolve queries through a different compilation path" than standard WHERE clause subqueries.

**Root cause hypothesis invalidated**: All previous diagnoses (H1-H3) targeted lookup processing (`In.process_rhs`, `RelatedIn.as_sql`) and query resolution (`resolve_expression`, `set_values`), but these are for WHERE clause subqueries. The test failure is in HAVING clause query compilation, which likely has a separate code path that bypasses all the attempted fix locations.

**Re-enter route**: **recon** - The diagnosis missed the actual code path. Need to investigate how subqueries are compiled specifically in HAVING/GROUP BY contexts rather than standard lookups.

