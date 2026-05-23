# Hypothesis graph: django__django-13158

## H₀ (Baseline - Abduction)
**Status**: Root cause identified  
**Timestamp**: 2026-05-23  

The tests fail because when `.none()` is called on a combined query (union/intersection/difference), it returns all results instead of an empty queryset.

**Test failure**:
- `test_union_none` expects `qs3.none()` to return `[]`
- Actually returns `<QuerySet [<Number: 0>, <Number: 1>, <Number: 8>, <Number: 9>]>`

## H₁ (Root Cause - Deduction)
**Status**: Active hypothesis  
**Confidence**: 95% (deduction - traced through code)  
**Timestamp**: 2026-05-23  

**Root cause**: The `get_combinator_sql()` method in `django/db/models/sql/compiler.py` does not check if the outer query is empty before compiling combined queries.

**How combined queries work**:
1. When `qs1.union(qs2)` is called, `_combinator_query()` creates a clone and sets:
   - `clone.query.combined_queries = (qs1.query, qs2.query)`
   - `clone.query.combinator = 'union'`
2. When `.none()` is called on the combined query:
   - `none()` calls `self._chain()` to create a clone
   - Then calls `clone.query.set_empty()` which adds a `NothingNode` to the OUTER query's WHERE clause
3. When the query is executed:
   - `as_sql()` sees `self.query.combinator` is set, calls `get_combinator_sql()`
   - `get_combinator_sql()` only compiles the inner queries from `combined_queries`
   - It filters out empty inner queries: `for query in self.query.combined_queries if not query.is_empty()`
   - **But it never checks if the OUTER query (self.query) is empty**
   - So the NothingNode in the outer WHERE clause is completely ignored

**Supporting evidence**:
- `django/db/models/query.py:919-923` - `none()` calls `set_empty()` on the cloned query
- `django/db/models/sql/query.py:1778-1779` - `set_empty()` adds `NothingNode` to `self.where`
- `django/db/models/sql/compiler.py:433-486` - `get_combinator_sql()` never checks `self.query.is_empty()`
- `django/db/models/sql/compiler.py:437` - Only checks if inner queries are empty: `if not query.is_empty()`
- `django/db/models/sql/compiler.py:504-507` - When combinator is set, `as_sql()` only calls `get_combinator_sql()` and returns

**What needs to change**: In `get_combinator_sql()`, check if the outer query is empty at the beginning, and if so, raise `EmptyResultSet`.

## Edit Sites

### Primary fix location
- `django/db/models/sql/compiler.py` lines 433-438: Add check for `self.query.is_empty()` at the beginning of `get_combinator_sql()` method, right after line 434. If the outer query is empty, raise `EmptyResultSet` to signal that no results should be returned.

## Gate iteration 1: PASS

**Fix applied:**
Added check in `get_combinator_sql()` to raise `EmptyResultSet` if outer query is empty.

```diff
--- a/django/db/models/sql/compiler.py
+++ b/django/db/models/sql/compiler.py
@@ -433,6 +433,8 @@ class SQLCompiler:
     def get_combinator_sql(self, combinator, all):
         features = self.connection.features
+        if self.query.is_empty():
+            raise EmptyResultSet
         compilers = [
             query.get_compiler(self.using, self.connection)
             for query in self.query.combined_queries if not query.is_empty()
```

**Gate result:**
```
test_union_none (queries.test_qs_combinators.QuerySetSetOperationTests) ... ok

----------------------------------------------------------------------
Ran 1 test in 0.002s

OK
```

**Codex review:** No functional objection. The fix correctly targets the root cause where `.none()` marks the outer combined query empty but `get_combinator_sql()` was ignoring the outer query's WHERE clause.

**Status:** RESOLVED — FAIL_TO_PASS test now passes.

## Audit (Full Gate - Phase 5)
**Timestamp**: 2026-05-23  
**Patch verified**: django/db/models/sql/compiler.py (+2 lines)

### FAIL_TO_PASS
- `test_union_none`: **PASS** ✓

### PASS_TO_PASS regressions
None - all 32 tests passed.

### Pre-existing failures (not counted)
None.

### Gate output summary
```
Ran 32 tests in 0.038s
OK (skipped=2)
```

All tests in `queries.test_qs_combinators.QuerySetSetOperationTests` passed, including the target test `test_union_none` which previously failed. The fix correctly raises `EmptyResultSet` when the outer combined query is marked empty via `.none()`, preventing the combinator from ignoring the outer query's empty state.

**VERDICT**: RESOLVED  
**RE-ENTER**: none

