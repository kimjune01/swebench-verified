# Hypothesis graph: django__django-14999

## H₁: RenameModel doesn't check if db_table actually changed
**Type**: Abduction  
**Confidence**: 95% (Deduction from code reading + experimental verification)

**Observation**: 
The test `test_rename_model_with_db_table_noop` expects 0 queries when renaming a model that has `db_table` set, but 5 queries are executed that recreate the Pony table in SQLite.

**Root Cause**:
In `django/db/migrations/operations/models.py`, the `RenameModel.database_forwards` method (lines 318-362) proceeds with database operations without checking if the actual database table name changed. 

When a model has `db_table='rider'` in its Meta options and is renamed from "Rider" to "Runner", the `db_table` option is preserved (confirmed by test at line 137 of state.py: `renamed_model = self.models[app_label, old_name_lower].clone()`). This means both `old_model._meta.db_table` and `new_model._meta.db_table` equal 'rider'.

The operation does:
1. Calls `alter_db_table()` which correctly returns early if old==new (line 470-472 of base/schema.py)
2. But then unconditionally loops through related_objects and calls `alter_field()` on all foreign keys (lines 328-346)
3. The `alter_field()` call causes SQLite to recreate the table even though nothing database-relevant changed

**Supporting Evidence**:
- `django/db/migrations/operations/models.py:318-362` - database_forwards doesn't check if db_table changed
- `django/db/migrations/state.py:137` - `renamed_model = self.models[app_label, old_name_lower].clone()` preserves options
- Test verification shows: `old_model._meta.db_table == new_model._meta.db_table == 'rider'`

**Edit Sites**:
- `django/db/migrations/operations/models.py` lines 318-362: Add early return in `database_forwards` if `old_model._meta.db_table == new_model._meta.db_table`
- `django/db/migrations/operations/models.py` lines 364-371: Same check needed in `database_backwards`

**Rejected Hypotheses**: None (first diagnosis)

**Open Questions**: None

## Craft iteration 1 - CONVERGED

**Hypothesis**: Early return in `database_forwards` when `old_model._meta.db_table == new_model._meta.db_table`

**Applied fix**:
- Added early return check in `RenameModel.database_forwards` (line 321-323)
- Check: if `old_model._meta.db_table == new_model._meta.db_table`, return immediately
- Did NOT modify `database_backwards` (codex caught lookup bug, method already delegates to forwards)

**Codex review feedback**:
- Warned: `database_backwards` lookup would be wrong (from_state has renamed model)
- Warned: Early return might skip necessary M2M work
- Suggested: Conditionally skip FK loop instead of blanket return
- Accepted: Let gate arbitrate between conservative (conditional) vs. aggressive (early return) fix

**Gate result**: ✓ PASS
- All 120 tests passed including FAIL_TO_PASS: `test_rename_model_with_db_table_noop`
- 0 queries executed as expected (test assertion: 0 != 0 no longer fails)

**Trajectory**: Convergent - first attempt resolved

**Edit location**: `django/db/migrations/operations/models.py:321-323`

## Audit: django__django-14999

### FAIL_TO_PASS
- `test_rename_model_with_db_table_noop`: **PASS** ✓

### PASS_TO_PASS regressions
None - all 120 tests passed.

### Pre-existing failures (not counted, confirmed against base capture)
None - base capture showed all tests passing (1 skipped for DB feature support).

### Kill report
Not applicable - patch is RESOLVED.

**Gate summary**: Ran 120 tests in 0.793s - OK (skipped=1)

**Verdict**: The craft patch successfully resolved the issue. The FAIL_TO_PASS test now passes (0 queries executed as expected), and no PASS_TO_PASS tests regressed. The early return when `old_model._meta.db_table == new_model._meta.db_table` correctly prevents unnecessary database operations while preserving all existing functionality.
