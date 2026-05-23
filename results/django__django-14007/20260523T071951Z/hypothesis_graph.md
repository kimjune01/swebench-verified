# Hypothesis graph: django__django-14007

## H₀: Initial Baseline Observation
**Mode**: Abduction  
**Confidence**: 99%  

The test `test_auto_field_subclass_create` fails because `obj.id` is an integer `1` instead of a `MyWrapper` instance. The test creates a `CustomAutoFieldModel` which uses `MyAutoField(BigAutoField)` with a custom `from_db_value` method that wraps integers in `MyWrapper`. After `objects.create()`, the id should be wrapped but is not.

Error:
```
AssertionError: 1 is not an instance of <class 'custom_pk.fields.MyWrapper'>
```

## H₁: Root Cause - Converters Not Applied on INSERT
**Mode**: Deduction  
**Confidence**: 98%  

Database converters (`from_db_value`) are not applied to `returning_fields` after INSERT operations.

**Evidence**:
1. `django/db/models/sql/compiler.py:1403-1421` - `SQLInsertCompiler.execute_sql` returns raw database values without applying converters:
   - Line 1415: `fetch_returned_insert_rows(cursor)` - bulk
   - Line 1418: `fetch_returned_insert_columns(cursor, self.returning_params)` - single RETURNING
   - Line 1419-1421: `last_insert_id(...)` - fallback

2. `django/db/models/base.py:874-875` - Values directly set without conversion:
   ```python
   for value, field in zip(results[0], returning_fields):
       setattr(self, field.attname, value)
   ```

3. `django/db/models/query.py:507, 521` - `bulk_create` has same issue:
   ```python
   setattr(obj_with_pk, field.attname, result)
   setattr(obj_without_pk, field.attname, result)
   ```

**Comparison with SELECT path**:
- `django/db/models/sql/compiler.py:1121-1130` - `results_iter` applies converters:
  ```python
  converters = self.get_converters(fields)
  if converters:
      rows = self.apply_converters(rows, converters)
  ```
- `get_converters` (line 1100) gathers `field.get_db_converters(connection)`
- `get_db_converters` (fields/__init__.py:746-749) returns `[self.from_db_value]` if present

The INSERT path bypasses this entire conversion mechanism.


## Edit Sites

**Primary fix location**: `django/db/models/sql/compiler.py:1403-1421`  
In `SQLInsertCompiler.execute_sql()`, apply field converters to returned values before returning them.

Steps:
1. Get converters for each field in `self.returning_fields` using `field.get_db_converters(self.connection)`
2. For each returned row/tuple, apply converters to corresponding values
3. Return the converted values

Pattern to follow (from `apply_converters` at line 1110-1119):
```python
for converter in converters:
    value = converter(value, expression, connection)
```

**Alternative (if needed)**: Apply converters at caller sites:
- `django/db/models/base.py:874-875` - In `_save_table` after `_do_insert`
- `django/db/models/query.py:507` - In `bulk_create` for objects with pk
- `django/db/models/query.py:521` - In `bulk_create` for objects without pk

The compiler-level fix is preferred as it's centralized and applies to all INSERT paths.

## Rejected Hypotheses

None - the root cause is directly observable in the code. The INSERT path demonstrably skips the converter application that the SELECT path performs.

## Open Questions

None - the fix location and pattern are clear from the existing `get_converters` and `apply_converters` methods in the same file.

## Craft Gate Loop

### Iteration 1 - Initial Fix Attempt
**Approach**: Applied converters using existing `get_converters()` method
**Change**: Modified `SQLInsertCompiler.execute_sql()` to:
- Restructure if-elif-else for three return paths
- Call `self.get_converters(self.returning_fields)` after fetching rows
- Apply converters to all three paths uniformly
- Convert back to tuples to preserve contract

**Gate Result**: DIVERGENT (AttributeError)
```
AttributeError: 'AutoField' object has no attribute 'output_field'
```

**Evidence**: `returning_fields` are Field objects, not expressions. The compiler's `get_converters()` method expects expressions with `output_field` attribute, but fields don't have this.

**Codex Feedback**: Recommended creating a dedicated helper method that wraps fields in SimpleNamespace to satisfy the converter API.

### Iteration 2 - Helper Method
**Approach**: Added `get_returning_field_converters()` helper method
**Change**: 
- Added `from types import SimpleNamespace` import
- Created `get_returning_field_converters(fields)` that wraps each field in `SimpleNamespace(output_field=field)`
- Gets both backend and field converters properly
- Updated `execute_sql()` to call the new helper instead of `get_converters()`

**Gate Result**: CONVERGENT (GREEN) ✓
```
test_auto_field_subclass_create (custom_pk.tests.CustomPKTests) ... ok
```

**All FAIL_TO_PASS tests passed**: YES
- `test_auto_field_subclass_create` ✓

The fix correctly applies `from_db_value` converters to auto-generated IDs returned from INSERT operations.

## Audit - Final Verification

### Phase 1: Patch Status
✓ Patch is live: `django/db/models/sql/compiler.py` modified (24 insertions, 6 deletions)

### Phase 2: Gate Results
All 15 tests executed (2 skipped for database feature requirements).

### Phase 3: Classification

**FAIL_TO_PASS**:
- `test_auto_field_subclass_create` (custom_pk.tests.CustomPKTests): **PASS** ✓

**PASS_TO_PASS** (all passing, zero regressions):
- test_get (custom_pk.tests.BasicCustomPKTests): PASS ✓
- test_in_bulk (custom_pk.tests.BasicCustomPKTests): PASS ✓
- test_pk_attributes (custom_pk.tests.BasicCustomPKTests): PASS ✓
- test_querysets (custom_pk.tests.BasicCustomPKTests): PASS ✓
- test_querysets_related_name (custom_pk.tests.BasicCustomPKTests): PASS ✓
- test_querysets_relational (custom_pk.tests.BasicCustomPKTests): PASS ✓
- test_save (custom_pk.tests.BasicCustomPKTests): PASS ✓
- test_custom_field_pk (custom_pk.tests.CustomPKTests): PASS ✓
- test_custom_pk_create (custom_pk.tests.CustomPKTests): PASS ✓
- test_unicode_pk (custom_pk.tests.CustomPKTests): PASS ✓
- test_unique_pk (custom_pk.tests.CustomPKTests): PASS ✓
- test_zero_non_autoincrement_pk (custom_pk.tests.CustomPKTests): PASS ✓

**Pre-existing failures**: None

**Regressions**: None

### Phase 4: Verdict
All FAIL_TO_PASS tests now pass. All PASS_TO_PASS tests remain passing. No regressions introduced.

VERDICT: RESOLVED
RE-ENTER: none
