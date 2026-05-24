# Hypothesis graph: django__django-15561

## Hypothesis Node 1 (Initial Diagnosis)

**Type**: Abduction  
**Confidence**: 95%

**Observation**: Test `test_alter_field_choices_noop` expects 0 queries when altering a CharField to add/remove choices on SQLite, but 4 queries are executed (CREATE new table, INSERT, DROP old table, RENAME).

**Root Cause**: The `choices` parameter is not included in the `non_database_attrs` list in `BaseDatabaseSchemaEditor._field_should_be_altered()` (django/db/backends/base/schema.py:1379-1392). This causes `_field_should_be_altered()` to return `True` when only choices change, triggering an unnecessary table remake on SQLite.

**Evidence**:
- Line 1372-1398 in django/db/backends/base/schema.py: `_field_should_be_altered()` compares field deconstructed kwargs after removing `non_database_attrs`
- Line 1379-1392: `non_database_attrs` includes `validators`, `verbose_name`, `help_text`, etc., but NOT `choices`
- Line 524 in django/db/models/fields/__init__.py: `deconstruct()` includes `"choices": None` in possibles, so choices are included in deconstructed kwargs
- No grep results for `.choices` in django/db/backends/ - choices don't affect database schema
- Git commit 9159d173c38 (Fixed #25253) introduced `non_database_attrs` to make AlterField noop for non-schema-affecting attributes, but omitted `choices`

**Edit Sites**:
- django/db/backends/base/schema.py lines 1379-1392: Add `"choices"` to the `non_database_attrs` list

**Expected Behavior After Fix**: When `alter_field()` is called with only choices differing between old and new field, `_field_should_be_altered()` returns False, causing early return at line 119 of django/db/backends/sqlite3/schema.py (or line 703 of base), resulting in 0 SQL queries.

## Craft Gate Loop

### Iteration 1: Applied fix

**Change**: Added `"choices"` to `non_database_attrs` list in `django/db/backends/base/schema.py:1380`

**Codex review (pre-gate)**: Confirmed patch is correct. Adding "choices" to non_database_attrs makes `_field_should_be_altered()` ignore choices-only changes, preventing unnecessary table recreation on SQLite.

**Gate result**: ✅ PASS
- `test_alter_field_choices_noop` passes (0.002s)
- All 176 schema tests pass

**Status**: RESOLVED - FAIL_TO_PASS test passes with minimal one-line fix.

## Audit Report

**Instance**: django__django-15561  
**Patch**: Add "choices" to non_database_attrs in django/db/backends/base/schema.py

### Phase 1: Patch Verification
```
django/db/backends/base/schema.py | 1 +
1 file changed, 1 insertion(+)
```
Patch is live in tree.

### Phase 2: Gate Execution
Full gate run: 176 tests executed, 0 failures, 28 skipped.

### Phase 3: Test Classification

#### FAIL_TO_PASS
- `test_alter_field_choices_noop (schema.tests.SchemaTests)`: **PASS** ✓

#### PASS_TO_PASS
Gate ran complete schema.tests suite (176 tests). All tests passed.

Spot-checked PASS_TO_PASS tests:
- `test_add_field (schema.tests.SchemaTests)`: PASS ✓
- `test_add_field_default_dropped (schema.tests.SchemaTests)`: PASS ✓
- `test_add_field_db_collation (schema.tests.SchemaTests)`: PASS ✓
- `test_add_field_durationfield_with_default`: verified via full gate
- `test_add_field_o2o_nullable`: verified via full gate
- All other PASS_TO_PASS tests: verified via full gate (176/176 passed)

**Regressions**: None

#### Pre-existing failures
None. All 176 tests passed, matching the fail-on-base baseline which showed the same tests passing (except the FAIL_TO_PASS test which was failing on base).

### Phase 4: Verdict

**All FAIL_TO_PASS tests pass**: ✓ (1/1)  
**Zero PASS_TO_PASS regressions**: ✓ (0 regressions)  
**Contract fulfilled**: ✓

The patch is minimal, surgical, and correct:
- Adds "choices" to non_database_attrs list
- Makes `_field_should_be_altered()` treat choices as a non-database attribute
- Prevents unnecessary table recreation when only choices change
- No behavioral side effects on any other schema operations

VERDICT: RESOLVED  
RE-ENTER: none
