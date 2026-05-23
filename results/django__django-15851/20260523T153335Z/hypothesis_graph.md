# Hypothesis graph: django__django-15851

## Hypothesis H₁ (initial diagnosis)
**Mode**: Deduction  
**Confidence**: 99%  
**Status**: Active

### Observation
Test `test_parameters` in `tests/dbshell/test_postgresql.py` line 155 fails with:
```
AssertionError: Tuples differ: (['psql', 'dbname', '--help'], None) != (['psql', '--help', 'dbname'], None)
```

Expected: `['psql', '--help', 'dbname']` (parameters before database name)  
Actual: `['psql', 'dbname', '--help']` (database name before parameters)

### Root cause
In `django/db/backends/postgresql/client.py` lines 36-40, the code constructs psql arguments in the wrong order:

```python
if dbname:
    args += [dbname]
args.extend(parameters)
```

PostgreSQL's `psql` command-line tool requires all options to come **before** the database name positional argument. The current implementation appends parameters after the database name, causing psql to ignore them with warnings.

### Supporting evidence
- `django/db/backends/postgresql/client.py:36-40` — database name added first, then parameters extended
- psql documentation requires: `psql [OPTION]... [DBNAME [USERNAME]]`
- Test expectation: `['psql', '--help', 'dbname']` confirms options must precede dbname

### Proposed fix
Swap the order in `django/db/backends/postgresql/client.py` lines 37-40:
1. Extend parameters first: `args.extend(parameters)`
2. Then add database name: `if dbname: args += [dbname]`

### Edit sites
- `django/db/backends/postgresql/client.py` lines 36-40


## craft gate loop

### Iteration 1
**Action**: Swapped order of `args.extend(parameters)` and `if dbname: args += [dbname]` in `django/db/backends/postgresql/client.py` (lines 35-37).

**Diff**:
```diff
--- a/django/db/backends/postgresql/client.py
+++ b/django/db/backends/postgresql/client.py
@@ -33,8 +33,8 @@ class DatabaseClient(BaseDatabaseClient):
             args += ["-h", host]
         if port:
             args += ["-p", str(port)]
+        args.extend(parameters)
         if dbname:
             args += [dbname]
-        args.extend(parameters)
 
         env = {}
```

**Codex review**: Approved. Directionally correct; parameters must precede dbname for psql command-line syntax. No structural issues identified.

**Gate outcome**: ✅ PASS — all 10 tests passed (9 ok, 1 skipped). `test_parameters` now passes.

**Resolution**: Fixed on first iteration. Parameters are now correctly positioned before the database name in psql invocations.


## Audit: django__django-15851

### FAIL_TO_PASS
- `test_parameters` - **PASS** ✓ (was FAIL on base)

### PASS_TO_PASS regressions
None - all PASS_TO_PASS tests continue to pass:
- test_accent - ok ✓
- test_basic - ok ✓
- test_column - ok ✓
- test_crash_password_does_not_leak - ok ✓
- test_nopass - ok ✓
- test_passfile - ok ✓
- test_service - ok ✓
- test_ssl_certificate - ok ✓

### Pre-existing (not counted)
- test_sigint_handler - skipped (requires PostgreSQL connection, already skipped on base)

### Gate output
All 10 tests passed (9 ok, 1 skipped). The FAIL_TO_PASS test now passes, and zero regressions introduced.

**VERDICT**: RESOLVED  
**RE-ENTER**: none
