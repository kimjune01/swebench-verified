# Hypothesis graph: django__django-16560

## H₀ (abduction, 85%)
**Status:** Initial diagnosis
**Timestamp:** 2026-05-23

The tests fail because the `violation_error_code` parameter is not implemented in the constraint classes. Tests expect to:
1. Pass `violation_error_code` as a parameter to BaseConstraint/CheckConstraint/UniqueConstraint constructors
2. Have it stored as an instance attribute
3. Have it included in equality comparisons, repr, and deconstruct
4. Have ValidationError raised with this code in the validate() methods

**Evidence:**
- Test error at line 81: `TypeError: BaseConstraint.__init__() got an unexpected keyword argument 'violation_error_code'`
- Test error at line 162: `TypeError: CheckConstraint.__init__() got an unexpected keyword argument 'violation_error_code'`  
- Test assertion failure at line 823: `AssertionError: None != 'custom_code'` - code is not being passed to ValidationError

**Supporting code locations:**
- `django/db/models/constraints.py:25-46` - BaseConstraint.__init__() only accepts name and violation_error_message
- `django/db/models/constraints.py:115` - CheckConstraint.validate() raises ValidationError without code parameter
- `django/db/models/constraints.py:388,394,403` - UniqueConstraint.validate() raises ValidationError without code parameter

**Root cause:** Missing implementation of violation_error_code feature across all constraint classes.

## Gate Loop - craft iteration 1

**Action:** Drafted and applied violation_error_code feature following recon diagnosis
**Changes:**
- Added `violation_error_code` class attribute to BaseConstraint
- Added `violation_error_code` parameter to BaseConstraint.__init__, deconstruct, and positional args handling
- Added `violation_error_code` parameter to CheckConstraint.__init__ and passed to super
- Updated CheckConstraint.validate() to pass code to ValidationError
- Updated CheckConstraint.__repr__() to include violation_error_code
- Updated CheckConstraint.__eq__() to compare violation_error_code
- Added `violation_error_code` parameter to UniqueConstraint.__init__ and passed to super
- Updated UniqueConstraint.validate() to pass code to ValidationError in all 3 locations
- Updated UniqueConstraint.__repr__() to include violation_error_code  
- Updated UniqueConstraint.__eq__() to compare violation_error_code

**Result:** All FAIL_TO_PASS tests pass (128 tests, OK, 54 skipped)
**Status:** RESOLVED ✓

The fix mirrors the existing `violation_error_message` pattern throughout all three constraint classes (BaseConstraint, CheckConstraint, UniqueConstraint), adding the new `violation_error_code` attribute that gets passed to ValidationError's code parameter during constraint validation.

---

# Audit: django__django-16560

**Timestamp:** 2026-05-23
**Gate results:** Ran 128 tests in 0.043s — OK (skipped=54)

## FAIL_TO_PASS
- test_custom_violation_code_message (constraints.tests.BaseConstraintTests.test_custom_violation_code_message): PASS ✓
- test_deconstruction (constraints.tests.BaseConstraintTests.test_deconstruction): PASS ✓
- test_eq (constraints.tests.CheckConstraintTests.test_eq): PASS ✓
- test_repr_with_violation_error_code (constraints.tests.CheckConstraintTests.test_repr_with_violation_error_code): PASS ✓
- test_validate_custom_error (constraints.tests.CheckConstraintTests.test_validate_custom_error): PASS ✓
- test_eq (constraints.tests.UniqueConstraintTests.test_eq): PASS ✓
- test_repr_with_violation_error_code (constraints.tests.UniqueConstraintTests.test_repr_with_violation_error_code): PASS ✓

## PASS_TO_PASS regressions
None. All 128 tests passed with 54 skipped (PostgreSQL-specific tests, expected).

## Pre-existing failures
None (all skipped tests were PostgreSQL-specific, expected behavior on SQLite).

## Verdict
All FAIL_TO_PASS tests now pass. Zero regressions in PASS_TO_PASS tests. The patch successfully implements the `violation_error_code` parameter across BaseConstraint, CheckConstraint, and UniqueConstraint following the existing `violation_error_message` pattern.

VERDICT: RESOLVED
RE-ENTER: none
