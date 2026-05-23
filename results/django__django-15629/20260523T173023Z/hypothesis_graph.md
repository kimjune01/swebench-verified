# Hypothesis graph: django__django-15629

## Hypothesis Node: H1 - Missing FK Collation Propagation
**Type**: Abduction (pattern-based from code inspection)  
**Confidence**: 85%  
**Status**: Active

### Observation
Two tests fail with `AssertionError: None != 'nocase'`:
1. `test_create_fk_models_to_pk_field_db_collation` - FK column has no collation when created
2. `test_alter_field_pk_fk_db_collation` - FK column collation not updated when PK collation changes

### Root Cause
Foreign key columns don't inherit `db_collation` from their target fields in two scenarios:

**Scenario 1: FK Creation**
- `ForeignKey.db_parameters()` (django/db/models/fields/related.py:1182) returns `{"type": ..., "check": ...}` but omits `collation`
- CharField/TextField override `db_parameters()` to add `db_params["collation"] = self.db_collation`
- ForeignKey doesn't look at `target_field.db_collation` when building db_parameters

**Scenario 2: PK Alteration**
- `BaseDatabaseSchemaEditor._alter_field()` (django/db/backends/base/schema.py:1031-1047) updates FK column types when PK changes
- It calls `_alter_column_type_sql()` but not `_alter_column_collation_sql()`
- The collation from the PK field's `db_parameters` is never propagated to FK columns

### Supporting Evidence
```python
# django/db/models/fields/related.py:1182
def db_parameters(self, connection):
    return {"type": self.db_type(connection), "check": self.db_check(connection)}
# Missing: collation key
```

```python
# django/db/backends/base/schema.py:1031-1047
for old_rel, new_rel in rels_to_update:
    rel_db_params = new_rel.field.db_parameters(connection=self.connection)
    rel_type = rel_db_params["type"]  # Only uses type, ignores collation
    fragment, other_actions = self._alter_column_type_sql(...)
```

### Edit Sites

**Site 1**: `django/db/models/fields/related.py` lines 1182-1183
- Modify `ForeignKey.db_parameters()` to include collation from `target_field`
- Check if `target_field` has `db_collation` attribute and include it

**Site 2**: `django/db/backends/base/schema.py` lines 1031-1047
- When updating FK columns after PK alteration, handle collation changes
- Check if `rel_db_params` contains collation and apply via `_alter_column_collation_sql()`

### Rejected Alternatives
- None yet - this is the first hypothesis

## craft gate loop

**Iteration 1**: Applied initial fix - ForeignKey.db_parameters() to propagate collation from target_field, and base schema FK loop to call _alter_column_collation_sql() when collations differ. Gate result: test_create_fk_models_to_pk_field_db_collation PASS, test_alter_field_pk_fk_db_collation FAIL (None != 'nocase').

**Iteration 2**: Volleyed with codex - identified that both old_rel and new_rel resolve through NEW model state, so comparing FK collations doesn't work. Changed to compare PK field collations directly (pk_collation_changed = old_db_params != new_db_params). Gate result: Still FAIL (None != 'nocase').

**Iteration 3**: Added PK collation change detection to populate rels_to_update - the FK loop wasn't executing because rels_to_update was empty (only populated when type changes, not collation). Added check for PK collation change to extend rels_to_update. Gate result: Still FAIL (None != 'nocase').

**Iteration 4**: Volleyed with codex - identified that SQLite overrides _alter_field() and uses table remakes instead of ALTER COLUMN. The base schema fix doesn't help SQLite. Fixed django/db/backends/sqlite3/schema.py line 458 to include collation changes in the remake condition: `if new_field.unique and (old_type != new_type or old_collation != new_collation)`. Gate result: ALL TESTS PASS.

**Resolution**: Fixed in 4 iterations. Three files modified:
1. `django/db/models/fields/related.py` - ForeignKey.db_parameters() propagates collation from target_field
2. `django/db/backends/base/schema.py` - Added PK collation change detection to populate rels_to_update, and FK loop to apply collation changes
3. `django/db/backends/sqlite3/schema.py` - Added collation change to remake condition

---

# Audit: django__django-15629

## FAIL_TO_PASS
- test_alter_field_pk_fk_db_collation (AlterField operation of db_collation on primary keys changes any FKs): **PASS** ✅
- test_create_fk_models_to_pk_field_db_collation (Creation of models with a FK to a PK with db_collation): **PASS** ✅

## PASS_TO_PASS regressions
None - all 123 tests in the gate passed with OK status.

## Pre-existing failures (not counted, confirmed against base capture)
None - the fail-on-base capture showed all visible tests passing before the patch.

## Kill report
Not applicable - patch is RESOLVED.

**Gate results**: Ran 123 tests in 0.851s - OK (skipped=1)

Both FAIL_TO_PASS tests now pass, and no regressions were introduced. The fix successfully:
1. Propagates db_collation from PK to FK columns during model creation
2. Updates FK column collations when PK collation is altered via AlterField
3. Handles SQLite's table remake requirements for collation changes

VERDICT: RESOLVED
RE-ENTER: none

