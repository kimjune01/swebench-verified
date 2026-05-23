# Hypothesis graph: django__django-13807

## Hypothesis H₁ - SQL identifiers not quoted in check_constraints

**Type**: Abduction → Deduction (confirmed via code inspection)
**Timestamp**: Initial recon pass
**Confidence**: 99% (deduction)

### Observation
Test `test_check_constraints_sql_keywords` fails with:
```
sqlite3.OperationalError: near "order": syntax error
```
when calling `connection.check_constraints(table_names=['order'])` on a model with `db_table='order'`.

### Hypothesis
The `check_constraints` method in `django/db/backends/sqlite3/base.py` does not quote table and column names when constructing SQL statements. When these identifiers are SQL keywords, SQLite cannot parse the statements.

### Evidence
1. **Direct observation** - Line 330: `'PRAGMA foreign_key_check(%s)' % table_name` uses bare string interpolation
2. **Direct observation** - Line 336: `'PRAGMA foreign_key_list(%s)' % table_name` uses bare string interpolation
3. **Direct observation** - Lines 341-342: SELECT statement interpolates `primary_key_column_name`, `column_name`, and `table_name` without quoting
4. **Contrast** - `introspection.py:85` correctly uses: `'PRAGMA table_info(%s)' % self.connection.ops.quote_name(table_name)`
5. **Contrast** - `introspection.py:227` correctly uses: `'PRAGMA foreign_key_list(%s)' % self.connection.ops.quote_name(table_name)`
6. **Mechanism** - `operations.py:170-173` defines `quote_name()` to wrap identifiers in double quotes

### Predicted fix
Apply `self.ops.quote_name()` to all table and column identifiers in:
- Line 330: `self.ops.quote_name(table_name)` in PRAGMA foreign_key_check
- Line 336: `self.ops.quote_name(table_name)` in PRAGMA foreign_key_list
- Lines 341-342: Quote `primary_key_column_name`, `column_name`, and `table_name` in SELECT

### Classification
**Root cause**: Missing identifier quoting in SQL construction
**Reasoning mode**: Deduction - traced through code, identified exact lines, confirmed correct pattern exists elsewhere
**Status**: Ready for craft

## Gate Loop - Craft Phase

### Iteration 1: Initial Fix Applied

**Changes made:**
- Line 330: Added `self.ops.quote_name(table_name)` to PRAGMA foreign_key_check
- Line 336: Added `self.ops.quote_name(table_name)` to PRAGMA foreign_key_list  
- Line 342: Added `self.ops.quote_name()` to all three identifiers (primary_key_column_name, column_name, table_name) in SELECT statement

**codex pre-gate review:** Confirmed fix is directionally correct, validates that SQLite accepts quoted identifiers in PRAGMA statements and SELECT. No blocking issues identified.

**Gate result:** ✅ PASS - All 50 tests passed (9 skipped), including FAIL_TO_PASS test `test_check_constraints_sql_keywords`

**Resolution:** RESOLVED - The minimal fix successfully quotes all SQL identifiers in the check_constraints method, allowing SQLite to properly handle reserved keywords like "order", "select", and "where" as table and column names.

---

## Audit: django__django-13807

**Timestamp**: Final verification
**Patch status**: Live (3 insertions, 3 deletions in django/db/backends/sqlite3/base.py)

### FAIL_TO_PASS
- `test_check_constraints_sql_keywords (backends.tests.FkConstraintsTests)`: **PASS** ✓

### PASS_TO_PASS regressions
**None** - All 41 executed PASS_TO_PASS tests passed (9 skipped as expected):
- ✓ `test_can_reference_existent (backends.tests.DBConstraintTestCase)`
- ✓ `test_can_reference_non_existent (backends.tests.DBConstraintTestCase)`
- ✓ `test_many_to_many (backends.tests.DBConstraintTestCase)`
- ✓ `test_django_date_extract (backends.tests.DateQuotingTest)`
- ✓ `test_parameter_escaping (backends.tests.EscapingChecks)`
- ✓ `test_paramless_no_escaping (backends.tests.EscapingChecks)`
- ✓ `test_bad_parameter_count (backends.tests.ParameterHandlingTest)`
- ✓ `test_generic_relation (backends.tests.SequenceResetTest)`
- ✓ All other backends tests (50 total, 41 executed)

### Pre-existing failures
**None** - No failures observed in either the fail-on-base capture or the gate run.

### Verification against baseline
Cross-checked gate output against the fail-on-base capture:
- Baseline showed all tests passing (with expected skips)
- Gate shows all tests passing (with same expected skips)
- Zero regressions introduced

### Kill report
Not applicable - patch is RESOLVED.

**VERDICT**: RESOLVED  
**RE-ENTER**: none
