# Hypothesis Graph: django__django-12858

## H₀ (Initial Abduction)
**Status**: Confirmed → Upgraded to Root Cause
**Mode**: Deduction (95%)
**Claim**: The test fails because models.E015 is raised when ordering contains `test__isnull`, even though `isnull` is a valid lookup.

**Evidence**:
- Test expects `Model.check()` to return `[]` for ordering `('test__isnull',)`
- Actual result: `[<Error: ... id='models.E015'>]`
- Error message: "'ordering' refers to the nonexistent field, related field, or lookup 'test__isnull'."

## H₁ (Root Cause - Deduction 98%)
**File**: `django/db/models/base.py`
**Lines**: 1750
**Claim**: The validation code only checks `fld.get_transform(part)` but does not check `fld.get_lookup(part)`, causing it to reject valid lookups that are not transforms.

**Supporting Evidence**:
1. Line 1750: `if fld is None or fld.get_transform(part) is None:`
2. Experimental verification:
   - `CharField().get_transform('isnull')` → `None`
   - `CharField().get_lookup('isnull')` → `<class 'django.db.models.lookups.IsNull'>`
3. `IsNull` inherits from `BuiltinLookup` → `Lookup` (not `Transform`)
4. Code trace for `test__isnull`:
   - Part 'test': finds CharField, sets `fld`, `_cls = None` (not a relation)
   - Part 'isnull': `_cls` is None → AttributeError → exception handler
   - Exception handler checks `fld.get_transform('isnull')` → `None` → raises E015
   - BUT should also check `fld.get_lookup('isnull')` → `IsNull` class → valid

**Historical Context**:
- Introduced in commit 440505cb2c (Fixed #29408) which added validation for related fields and lookups
- The comment mentions "lookups" but the code only validates transforms
- Prior test `test_ordering_allows_registered_lookups` uses `test__lower` which is a Transform, so it passes

## Edit Sites

**Primary Edit**:
- `django/db/models/base.py` line 1750
- Change: `if fld is None or fld.get_transform(part) is None:`
- To: `if fld is None or (fld.get_transform(part) is None and fld.get_lookup(part) is None):`
- Rationale: Accept both transforms AND lookups as valid ordering terms

**Verification**:
- After fix, `test_ordering_pointing_to_lookup_not_transform` should pass
- Existing `test_ordering_allows_registered_lookups` should still pass (transforms are also lookups conceptually)
- Runtime behavior already works (per problem description), validation should match

## Craft: Gate Loop

### Iteration 1

**Fix applied**: Changed line 1750 in `django/db/models/base.py` from:
```python
if fld is None or fld.get_transform(part) is None:
```
to:
```python
if fld is None or (fld.get_transform(part) is None and fld.get_lookup(part) is None):
```

**codex pre-gate review**: No blocking issue. Fix correctly recognizes `isnull` as a registered lookup. Noted concerns about whether all lookups should be allowed (broader design question).

**Gate result**: ✅ PASS - All 76 tests passed including `test_ordering_pointing_to_lookup_not_transform`

**Trajectory**: Convergent success - FAIL_TO_PASS test now passes, no regressions.

---

# Audit: django__django-12858

## Patch Status
✅ Patch is live: `django/db/models/base.py` (1 insertion, 1 deletion)

## Gate Results
Full gate executed: 76 tests run in 0.084s
Status: **OK** (skipped=2)

## FAIL_TO_PASS
- `test_ordering_pointing_to_lookup_not_transform`: **PASS** ✅
  - Was FAILING on base (confirmed in fail-on-base capture)
  - Now PASSING after patch

## PASS_TO_PASS Regressions
**None** - all PASS_TO_PASS tests continue to pass

Confirmed passing (sample):
- test_check_constraints: ok
- test_ordering_allows_registered_lookups: ok
- test_ordering_pointing_to_foreignkey_field: ok
- test_ordering_pointing_to_missing_field: ok
- test_ordering_pointing_multiple_times_to_model_fields: ok
- All 76 tests in gate: ok

## Pre-existing Failures (not counted)
**None** - no failures in gate output

## Contract Verification
✅ All FAIL_TO_PASS tests pass (1/1)
✅ Zero PASS_TO_PASS regressions (0)
✅ Patch successfully fixes the validation logic without side effects

VERDICT: RESOLVED
RE-ENTER: none
