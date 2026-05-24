# Hypothesis graph: django__django-15930

## Hypothesis H0 (abduction)
**Timestamp:** 2026-05-23 (initial recon)
**Status:** Active
**Confidence:** 95% (deduction)

The tests fail because `When(~Q(pk__in=[]), then=...)` compiles to invalid SQL: `WHEN THEN ...` (missing condition).

**Root cause:**
When `~Q(pk__in=[])` is compiled:
1. The `In` lookup raises `EmptyResultSet` for the empty list
2. `WhereNode.as_sql` catches this and returns `"", []` for a negated node (meaning "matches everything")
3. `When.as_sql` at line 1300 doesn't handle empty `condition_sql`, resulting in invalid template substitution

**Evidence:**
- `django/db/models/lookups.py:439` - In.process_rhs raises EmptyResultSet when rhs is empty
- `django/db/models/sql/where.py:122` - WhereNode.as_sql returns `"", []` when `empty_needed == 0` and `self.negated == True`
- `django/db/models/expressions.py:1300` - When.as_sql directly uses condition_sql without checking if it's empty

**Edit sites:**
- `django/db/models/expressions.py` lines 1296-1307 (When.as_sql method)
  - After line 1300 (`condition_sql, condition_params = compiler.compile(self.condition)`), check if condition_sql is empty
  - If empty, replace with always-true expression: `"1=1"` or compile `Value(True)` depending on database support
  - Pattern exists in Exists.as_sql at line 1494-1500

**Supporting quote from WhereNode.as_sql docstring:**
> Return the SQL version of the where clause and the value to be substituted in. Return '', [] if this node matches everything


## Craft iteration 1 (RESOLVED)

**Fix applied:** Added empty condition check in `When.as_sql` after line 1301.

```python
condition_sql, condition_params = compiler.compile(self.condition)
if not condition_sql:
    # Empty condition means "matches everything" (always true)
    condition_sql = "1=1"
    condition_params = ()
```

**Codex feedback:** 
- Don't use `supports_boolean_expr_in_select_clause` flag - just use `1=1` as the safe predicate
- The fix addresses the immediate crash (empty SQL in WHEN clause)
- Broader optimizations (FullResultSet handling, EmptyResultSet) are separate concerns

**Gate result:** ✅ PASS - All 89 tests passed including `test_annotate_with_full_when`

**Resolution:** The fix correctly handles the case where `~Q(pk__in=[])` compiles to an empty string by replacing it with the SQL literal `1=1`, producing valid `WHEN 1=1 THEN ...` syntax instead of invalid `WHEN THEN ...`.

## Audit: django__django-15930

**Timestamp:** 2026-05-23

### FAIL_TO_PASS
- `test_annotate_with_full_when (expressions_case.tests.CaseExpressionTests)`: **PASS** ✅

### PASS_TO_PASS regressions
None. All 89 tests passed cleanly.

### Pre-existing failures (not counted, confirmed against base capture)
None. The only failure on base was `test_annotate_with_full_when` (ERROR), which is the FAIL_TO_PASS test that now passes.

### Patch summary
```diff
django/db/models/expressions.py | 4 ++++
```

The fix adds a guard in `When.as_sql()` (lines 1302-1305) to handle empty condition SQL:
- When `condition_sql` is empty (meaning "matches everything"), replaces it with `"1=1"`
- This prevents invalid SQL like `WHEN THEN ...` from being generated
- Correctly produces `WHEN 1=1 THEN ...` for cases like `When(~Q(pk__in=[]), then=...)`

### Verification
Gate ran all 89 tests in expressions_case.tests suite. All passed, including:
- The target FAIL_TO_PASS test
- All 88 PASS_TO_PASS tests with no regressions
- All documentation examples
- All Case/When expression tests across multiple database field types

VERDICT: RESOLVED
RE-ENTER: none
