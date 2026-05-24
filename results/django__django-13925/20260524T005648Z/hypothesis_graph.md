# Hypothesis graph: django__django-13925

## H₀: Initial Abduction
**Type**: Abduction  
**Confidence**: 85%

The tests fail because `_check_default_pk` raises W042 warnings on child models that inherit their primary key from parent models, even though these child models shouldn't be flagged (the warning should only appear on the parent that introduces the auto-created pk).

**Evidence**:
- `test_explicit_inherited_pk` expects no warnings when Parent has explicit pk, Child inherits → actual: W042 on Child
- `test_auto_created_inherited_pk` expects W042 only on Parent → actual: W042 on both Parent and Child

## H₁: Root Cause - Deduction
**Type**: Deduction  
**Confidence**: 98%

In multi-table inheritance, Django creates a OneToOneField with `auto_created=True` and `parent_link=True` for the child model's primary key. The `_check_default_pk` method at `django/db/models/base.py:1299-1320` checks `cls._meta.pk.auto_created` without distinguishing between:
1. A model that introduces its own auto-created pk (should warn)
2. A child model whose pk is a parent link (should NOT warn)

**Supporting Evidence**:
- `django/db/models/base.py:1301`: Checks only `cls._meta.pk.auto_created`
- `django/db/models/base.py:253-257`: Creates parent_ptr with `auto_created=True, parent_link=True`
- `django/db/models/options.py:274-284`: Promotes parent link to be child's primary key
- Empirical test shows Child._meta.pk.auto_created == True even when Parent has explicit pk

**Code Path**:
1. Model metaclass creates OneToOneField parent_ptr for child (base.py:253)
2. Options._prepare promotes parent_ptr to be pk (options.py:274)
3. Model.check calls _check_default_pk (base.py:1293)
4. _check_default_pk sees auto_created=True on child's pk, raises W042 incorrectly

## Craft: Gate loop

### Iteration 1: Draft and volley

**Draft:** Added early return in `_check_default_pk` to skip child models whose pk is an auto-created parent link.

**Codex feedback:** Tighten the condition to also check `cls._meta.pk.auto_created` for semantic precision. The original draft would skip any parent-link OneToOneField, not just auto-created ones.

**Revision applied:** Changed condition from:
```python
if isinstance(cls._meta.pk, OneToOneField) and cls._meta.pk.remote_field.parent_link:
```
to:
```python
if cls._meta.pk.auto_created and isinstance(cls._meta.pk, OneToOneField) and cls._meta.pk.remote_field.parent_link:
```

**Gate result:** ✅ PASS - All 26 tests passed, including both FAIL_TO_PASS:
- test_auto_created_inherited_pk
- test_explicit_inherited_pk

**Status:** RESOLVED

## Audit: Regression Verification

### Patch verification
The craft patch is live in the tree:
```
 django/db/models/base.py | 6 ++++++
 1 file changed, 6 insertions(+)
```

### Full gate results
All 26 tests passed (0.040s).

### FAIL_TO_PASS classification
- ✅ test_auto_created_inherited_pk (check_framework.test_model_checks.ModelDefaultAutoFieldTests) — PASS
- ✅ test_explicit_inherited_pk (check_framework.test_model_checks.ModelDefaultAutoFieldTests) — PASS

### PASS_TO_PASS classification
All PASS_TO_PASS tests continue to pass. No regressions detected.

Sample PASS_TO_PASS results:
- test_app_default_auto_field — ok
- test_auto_created_inherited_parent_link — ok
- test_auto_created_pk — ok
- test_default_auto_field_setting — ok
- test_explicit_inherited_parent_link — ok
- test_explicit_pk — ok
- All ConstraintNameTests, DuplicateDBTableTests, and IndexNameTests — ok

### Pre-existing failures
None. All tests pass cleanly.

### Verdict
**RESOLVED** — All FAIL_TO_PASS tests now pass, and zero PASS_TO_PASS regressions were introduced. The fix correctly suppresses W042 warnings for child models with auto-created parent-link primary keys while preserving warnings for models that introduce their own auto-created pk.
