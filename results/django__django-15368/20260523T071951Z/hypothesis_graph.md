# Hypothesis graph: django__django-15368
## H₀: Type check too narrow for F() expressions (abduction)

**Symptom**: Test `test_f_expression` fails because `bulk_update()` converts plain `F('field')` expressions to their string representation 'F(field)' instead of resolving them to SQL column references.

**Evidence**:
- Test creates notes with `note='test_note'`, assigns `note.misc = F('note')`, calls `bulk_update(notes, ['misc'])`
- Expected: `misc` should contain 'test_note' (the value of the `note` field)
- Actual: 0 notes found with `misc='test_note'`, suggesting F() was not resolved

**Root cause**: Line 673 in `django/db/models/query.py` checks `isinstance(attr, Expression)` to determine if a value should be treated as an expression. However:
- `F` class inherits from `Combinable`, NOT from `Expression` (see `django/db/models/expressions.py:582`)
- `Expression` inherits from both `BaseExpression` AND `Combinable` (see `django/db/models/expressions.py`)
- Plain `F('field')` objects fail the `isinstance(attr, Expression)` check
- They get wrapped in `Value(attr, output_field=field)`, which converts the F object to its string repr

**Why test_field_references passes**: `F('num') + 1` creates a `CombinedExpression` (line 445 in expressions.py), which DOES inherit from `Expression`, so it passes the check.

**Fix location**: `django/db/models/query.py:673`
- Current: `if not isinstance(attr, Expression):`
- Should use duck typing: `if not hasattr(attr, 'resolve_expression'):`
- This pattern is already used throughout Django (expressions.py lines 59, 186, 1033, 1245)

**Confidence**: deduction — 95%
- Traced the exact code path from test to failure
- Verified class hierarchy shows F is not a subclass of Expression
- Confirmed duck-typing pattern is Django's standard approach

## Gate Loop - Iteration 1

**Hypothesis**: Change `isinstance(attr, Expression)` to `hasattr(attr, 'resolve_expression')` in `django/db/models/query.py:673` to handle `F` objects which inherit from `Combinable` rather than `Expression`.

**Implementation**:
- Line 673: Changed `if not isinstance(attr, Expression):` to `if not hasattr(attr, 'resolve_expression'):`
- Line 20: Removed unused `Expression` import

**Codex review**: No functional problems. Fix is directionally correct. Noted that hasattr is the right protocol check and matches Django's existing expression protocol.

**Gate result**: ✓ PASS - All 30 tests passed (0.402s)
- `test_f_expression` now passes: F('note') is correctly resolved as a column reference
- All existing tests continue to pass

**Evidence trajectory**: Convergent-success (hypothesis confirmed on first iteration)

**Resolution**: FAIL_TO_PASS test passes. Working tree contains the minimal fix.

---

# Audit: django__django-15368

## Patch verification
```
django/db/models/query.py | 4 ++--
1 file changed, 2 insertions(+), 2 deletions(-)
```

Changes:
- Line 20: Removed unused `Expression` import
- Line 673: Changed `isinstance(attr, Expression)` → `hasattr(attr, 'resolve_expression')`

## FAIL_TO_PASS
- `test_f_expression (queries.test_bulk_update.BulkUpdateTests)`: **PASS** ✓

## PASS_TO_PASS regressions
**None** — all 30 tests passed, including all listed PASS_TO_PASS tests:
- test_batch_size, test_foreign_keys_do_not_lookup, test_functions, test_multiple_fields
- test_set_field_to_null, test_set_mixed_fields_to_null, test_simple, test_unsaved_models
- test_booleanfield, test_custom_db_columns, test_custom_pk, test_datetime_field
- And 18 additional bulk_update tests (all ok)

## Pre-existing failures
**None** confirmed against base capture.

## Kill report
Not applicable — patch is RESOLVED.

VERDICT: RESOLVED
RE-ENTER: none
