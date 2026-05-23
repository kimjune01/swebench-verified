# Hypothesis Graph: django__django-15037

## H₀ (Abduction - Initial)
**Status**: Active
**Timestamp**: 2026-05-22 (recon phase 1)

The test `test_foreign_key_to_field` fails because inspectdb does not generate the `to_field` parameter when a foreign key references a non-primary-key field.

**Evidence**:
- Test expects: `to_field_fk = models.ForeignKey('InspectdbPeoplemoredata', models.DO_NOTHING, to_field='people_unique_id')`
- Actual output: `to_field_fk = models.ForeignKey('InspectdbPeoplemoredata', models.DO_NOTHING)`
- The `to_field='people_unique_id'` parameter is missing

## H₁ (Deduction - Root Cause)
**Status**: Active
**Timestamp**: 2026-05-22 (recon phase 3)
**Confidence**: 95% (deduction)

Root cause identified in `django/core/management/commands/inspectdb.py` lines 118-130.

When processing foreign key relations, the code:
1. Gets the referenced table name from `relations[column_name][1]`
2. Creates the ForeignKey/OneToOneField with the referenced model
3. **BUT** never checks or uses `relations[column_name][0]` (the referenced column name)

The `relations` dictionary from `get_relations()` contains:
- Key: column name in current table
- Value: tuple of (referenced_column_name, referenced_table_name)

**Supporting Evidence**:
- `django/core/management/commands/inspectdb.py:123-126` - only uses `relations[column_name][1]` for table name
- `django/db/backends/sqlite3/introspection.py:168` - `get_relations` returns `(other_name, table)` tuple
- `django/db/backends/postgresql/introspection.py:88` - returns `{row[0]: (row[2], row[1])}` where row[2] is referenced column
- All backend implementations follow same structure: `{field: (ref_column, ref_table)}`

**What needs to change**:
After determining the relation type and target (lines 118-130), the code must:
1. Extract the referenced column: `relations[column_name][0]`
2. Get the primary key of the referenced table
3. If referenced column != primary key, add `to_field=<referenced_column>` to `extra_params`

## Gate Loop (craft)

### Iteration 1: Initial fix
**Action:** Added logic after `rel_to` determination to extract the referenced column from `relations[column_name][0]`, get the PK of the referenced table, and add `to_field` to `extra_params` if they differ.

**codex pre-gate feedback:** Raised concern that `to_field` expects model field name, not raw DB column name. However, the test explicitly expects `to_field='people_unique_id'` (the column name), so proceeding to gate.

**Gate result:** ✓ PASS
- `test_foreign_key_to_field` ... ok (target FAIL_TO_PASS test now passes)
- 1 failure remains: `test_custom_fields` (pre-existing failure confirmed in baseline, unrelated to this fix)

**Evidence trajectory:** Convergent-resolved. The fix addresses the root cause identified in recon by using `relations[column_name][0]` to extract the referenced column and adding `to_field` when it differs from the PK.

**Resolution:** FAIL_TO_PASS test passes. Fix complete.

---

# Audit: django__django-15037

## Patch Status
✓ Patch is live: `django/core/management/commands/inspectdb.py` modified

## FAIL_TO_PASS
- `test_foreign_key_to_field (inspectdb.tests.InspectDBTestCase)` → **PASS** ✓

## PASS_TO_PASS regressions
None. All previously passing tests remain passing:
- `test_attribute_name_not_python_keyword` → ok
- `test_char_field_db_collation` → ok
- `test_digits_column_name_introspection` → ok
- `test_field_types` → ok
- `test_introspection_errors` → ok
- `test_json_field` → ok
- `test_managed_models` → ok
- `test_number_field_types` → ok
- `test_special_column_name_introspection` → ok
- `test_stealth_table_name_filter_option` → ok
- `test_table_name_introspection` → ok
- `test_table_option` → ok
- `test_text_field_db_collation` → ok
- `test_unique_together_meta` → ok
- `test_include_views` → ok

## Pre-existing (not counted, confirmed against base capture)
- `test_custom_fields (inspectdb.tests.InspectDBTestCase)` - This test was already failing on the base (unpatched) code with the same error (looking for 'text_field = myfields.TextField()' in output). This failure is unrelated to the foreign key to_field fix.

## Classification
The fix successfully resolves the target issue:
- The FAIL_TO_PASS test `test_foreign_key_to_field` now passes
- Zero regressions introduced
- The one failing test (`test_custom_fields`) was already failing on base

VERDICT: RESOLVED
RE-ENTER: none
