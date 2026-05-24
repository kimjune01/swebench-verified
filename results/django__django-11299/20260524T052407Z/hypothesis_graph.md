# Hypothesis graph: django__django-11299

## H₀: Initial Hypothesis (Abduction)
**Status**: Confirmed
**Type**: Root cause identified
**Confidence**: 95% (Deduction - traced through code)

The tests fail because `_add_q()` in `django/db/models/sql/query.py` does not propagate the `simple_col` parameter when recursively processing nested Q objects.

### Evidence
1. `build_where()` at line 1325 calls `_add_q(..., simple_col=True)` 
2. When `_add_q()` processes a child that is a Node (nested Q object), it recursively calls itself at lines 1339-1341 WITHOUT passing `simple_col`
3. The default value of `simple_col` parameter is `False` (line 1328)
4. This causes nested Q objects to use `Col` (with table prefix) instead of `SimpleCol` (without table prefix)

### Test Failure
- Test: `test_simplecol_query` expects all lookups to use `SimpleCol` when building WHERE with OR conditions
- Actual: Inner AND clause uses `Col` instead of `SimpleCol`
- Error: `AssertionError: Col(queries_author, queries.Author.num) is not an instance of <class 'django.db.models.expressions.SimpleCol'>`

### Impact on CheckConstraint
For CheckConstraint with `Q(field_1__isnull=False, flag__exact=True) | Q(flag__exact=False)`:
- The outer OR clause correctly uses `SimpleCol` for `flag`
- The inner AND clause incorrectly uses `Col` for `field_1` and `flag`, generating `"table"."field"` instead of `"field"`
- On SQLite, this breaks when the table is recreated during migrations, as the old table name no longer exists

### Edit Site
**File**: `django/db/models/sql/query.py`
**Lines**: 1339-1341
**Change**: Add `simple_col` parameter to the recursive `_add_q()` call

Current code:
```python
child_clause, needed_inner = self._add_q(
    child, used_aliases, branch_negated,
    current_negated, allow_joins, split_subq)
```

Should be:
```python
child_clause, needed_inner = self._add_q(
    child, used_aliases, branch_negated,
    current_negated, allow_joins, split_subq, simple_col)
```


## Craft gate-loop iteration 1

**Hypothesis**: The `_add_q()` method fails to propagate `simple_col` parameter in recursive calls for nested Q objects

**Edit applied**: Modified `django/db/models/sql/query.py` line 1341 to add `simple_col=simple_col` as a keyword argument to the recursive `_add_q()` call:
```python
child_clause, needed_inner = self._add_q(
    child, used_aliases, branch_negated,
    current_negated, allow_joins, split_subq, simple_col=simple_col)
```

**Pre-gate volley**: codex confirmed fix direction is correct, recommended using keyword argument instead of positional for safety

**Gate result**: ✓ PASS - All 105 tests passed, including `test_simplecol_query`

**E-value trajectory**: Convergent-resolved (test went from FAIL to PASS on first attempt)

**Status**: RESOLVED

## Audit: django__django-11299

**Patch verified**: `django/db/models/sql/query.py` line 1341 modified to propagate `simple_col=simple_col` parameter

### FAIL_TO_PASS
- `test_simplecol_query (queries.test_query.TestQuery)`: **PASS** ✓

### PASS_TO_PASS regressions
None - all 104 PASS_TO_PASS tests passed

### Pre-existing failures (not counted)
None - baseline already showed clean suite

### Gate results
```
Ran 105 tests in 0.906s
OK
```

All tests passing:
- The target test `test_simplecol_query` now passes
- Zero regressions introduced
- All migrations and queries tests healthy

**Classification**: The craft patch correctly fixed the `simple_col` propagation issue without introducing any side effects. The minimal one-line change (adding `simple_col=simple_col` to the recursive call) ensures that nested Q objects inherit the `simple_col` flag from their parent context.

