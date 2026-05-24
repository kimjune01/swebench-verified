# Hypothesis graph: django__django-16315

## H₀ (Abduction): Initial diagnosis - ON CONFLICT uses field names instead of db_column names

**Failure mode**: `sqlite3.OperationalError: no such column: EXCLUDED.name`

The test `test_update_conflicts_unique_fields_update_fields_db_column` creates a model with mixed-case db_column values:
- `rank` field with `db_column="rAnK"`
- `name` field with `db_column="oTheRNaMe"`

When calling `bulk_create()` with `update_conflicts=True, unique_fields=["rank"], update_fields=["name"]`, the generated SQL uses field names in the ON CONFLICT clause instead of the actual database column names.

**Evidence**:
- Error: `no such column: EXCLUDED.name` - the database expects "EXCLUDED.oTheRNaMe"
- Stack trace points to `django/db/models/sql/compiler.py:1778` executing SQL
- ON CONFLICT SQL generation is in backend operations files

**Suspect files**:
- `django/db/backends/postgresql/operations.py:352-366` - PostgreSQL implementation
- `django/db/backends/sqlite3/operations.py:415-429` - SQLite implementation  
- `django/db/backends/mysql/operations.py:436-458` - MySQL implementation

**Root cause**: 
The `on_conflict_suffix_sql()` method in all three backends receives `update_fields` and `unique_fields` as lists of field names (e.g., ["rank", "name"]) but uses them directly with `quote_name()` without converting them to database column names. This works fine when `db_column` is not set, but breaks when field names differ from column names.

**Call chain**:
1. `bulk_create()` at query.py:810,827 passes field names in `unique_fields` and `update_fields`
2. `_batched_insert()` at query.py:1856 forwards them to `_insert()`
3. `_insert()` at query.py:1816-1821 creates InsertQuery with the field names
4. Compiler at compiler.py:1725 calls `on_conflict_suffix_sql(fields, ..., update_fields, unique_fields)`
5. Backend operations quote the field names directly instead of looking up their column names

**Required fix**:
Each backend's `on_conflict_suffix_sql()` must:
1. Create a mapping from field.name to field.column using the `fields` parameter
2. Convert field names in `unique_fields` and `update_fields` to column names
3. Quote the column names, not the field names


## Gate iteration 1: PASS (converged)

**Hypothesis tested:** The ON CONFLICT SQL uses Python field names instead of database column names because the backend's `on_conflict_suffix_sql()` methods receive field name strings but don't have access to field metadata to convert them to column names.

**Fix applied:**
1. In `django/db/models/query.py` (bulk_create method, after line 797):
   - Added conversion of `update_fields` and `unique_fields` from field name strings to Field objects using `opts.get_field()`
   - This happens after `_check_bulk_create_options()` validation but before passing to `_batched_insert()`

2. In `django/db/models/sql/compiler.py` (line 1728-1729):
   - Changed from passing Field objects directly to extracting column names: `[f.column for f in self.query.update_fields or ()]`
   - Applied same pattern for unique_fields

**codex volley:**
- Draft 1: Tried fixing in backend operations.py files by creating field_map inside each backend
- codex feedback: Wrong layer - fix should be in compiler.py to avoid duplicating logic across backends
- Draft 2: Added `[f.column for f in ...]` in compiler.py
- codex feedback: Missing the query.py conversion - update_fields/unique_fields need to be Field objects first
- Draft 3: Added both conversions (query.py + compiler.py)
- codex approval: Correct approach

**Gate result:** All 51 tests pass, including the FAIL_TO_PASS test `test_update_conflicts_unique_fields_update_fields_db_column`

**SQL generated (verified correct):**
- Before: `ON CONFLICT("rank") DO UPDATE SET "name" = EXCLUDED."name"` (wrong - uses Python field names)
- After: `ON CONFLICT("rAnK") DO UPDATE SET "oTheRNaMe" = EXCLUDED."oTheRNaMe"` (correct - uses db_column values)

**Status:** RESOLVED

## Audit verification

**Patch confirmed live:**
- `django/db/models/query.py` (+5 lines)
- `django/db/models/sql/compiler.py` (+2/-2 lines)

**FAIL_TO_PASS results:**
- ✅ `test_update_conflicts_unique_fields_update_fields_db_column`: **PASS**

**PASS_TO_PASS regressions:** None

**Pre-existing failures:** None (all PASS_TO_PASS tests passed)

**Gate outcome:** 51 tests run, 51 passed (7 skipped), 0 failures

**Verdict:** RESOLVED - The fix correctly converts field names to db_column names in ON CONFLICT clauses. All FAIL_TO_PASS tests pass with zero regressions.
