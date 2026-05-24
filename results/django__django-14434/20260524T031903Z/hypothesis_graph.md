# Hypothesis graph: django__django-14434

## Hypothesis Node: H0_baseline
**Type**: abduction
**Confidence**: 95%
**Status**: active

The test `test_unique_constraint` fails because `sql.references_column(table, 'name')` returns `False` when it should return `True`.

**Error trace**:
```
AssertionError: False is not True
  File "/testbed/tests/schema/tests.py", line 2211, in test_unique_constraint
    self.assertIs(sql.references_column(table, 'name'), True)
```

## Hypothesis Node: H1_root_cause
**Type**: deduction
**Confidence**: 99%
**Status**: active

**Root cause**: In `django/db/backends/base/schema.py`, the `_create_unique_sql` method (line 1244) creates a `Table` object and passes it to `_index_columns`, but `_index_columns` expects a string table name, not a Table object.

**Evidence chain**:
1. Line 1244: `table = Table(model._meta.db_table, self.quote_name)` - creates Table object
2. Line 1254: `columns = self._index_columns(table, columns, ...)` - passes Table object
3. Line 1069: `_index_columns` returns `Columns(table, columns, ...)` - stores Table object as `self.table`
4. `django/db/backends/ddl_references.py` line 66: `TableColumns.references_column` does `return self.table == table and column in self.columns`
5. When `self.table` is a Table object and `table` param is a string, the comparison fails

**Comparison with correct pattern in `_create_index_sql`**:
- Line 1038: `table = model._meta.db_table` - stores as STRING
- Line 1051: `self._index_columns(table, columns, ...)` - passes STRING
- Line 1047: `table=Table(table, self.quote_name)` - creates Table object only for Statement

**Supporting evidence**:
- `_create_unique_sql` line 1256 correctly passes string: `Expressions(model._meta.db_table, ...)`
- This inconsistency within the same method confirms the bug

**Git history**: Commit 3aa545281e added expressions support but left the existing bug in place.


## Gate Loop: craft iteration 1

**Draft:** Applied recon's two-line fix:
- Line 1244: `table = model._meta.db_table` (store as string)
- Line 1259: `table=Table(table, self.quote_name),` (wrap in Table() at Statement construction)

**Codex volley:** No functional problems. Fix matches the pattern in `_create_index_sql`. Minimal and correct.

**Gate result:** GREEN — all 168 tests passed, including `test_unique_constraint`.

**Trajectory:** Convergent-success (fixed on first attempt)

**Resolution:** FAIL_TO_PASS test now passes. Working tree contains the complete fix.

## Audit: django__django-14434

**Patch status**: Live (2 insertions, 2 deletions in django/db/backends/base/schema.py)

### FAIL_TO_PASS
- test_unique_constraint (schema.tests.SchemaTests): **PASS** ✓

### PASS_TO_PASS regressions
**None** — all 167 other tests in the schema test suite passed.

### Pre-existing failures
**None** — baseline capture showed all tests passing except the target FAIL_TO_PASS test.

### Gate results
```
Ran 168 tests in 0.873s
OK (skipped=28)
```

All tests passed. The patch:
1. Fixed the FAIL_TO_PASS test by storing `table` as a string (line 1244) instead of a Table object
2. Correctly wraps the string in `Table()` only when constructing the Statement (line 1259)
3. Introduced zero regressions in the 167 PASS_TO_PASS tests

VERDICT: RESOLVED
RE-ENTER: none
