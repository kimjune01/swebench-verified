# Hypothesis graph: django__django-11163

## H₀ (Abduction)
**Claim**: The test `test_modelform_subclassed_model` fails because `model_to_dict(bw, fields=[])` returns all fields instead of an empty dict.

**Evidence**: Test output shows:
```
AssertionError: Lists differ: ['id', 'name', 'score', 'writer_ptr'] != []
```

**Reasoning**: When `fields=[]` is passed, the function should return only the fields in the list (none), but it returns all fields.

## H₁ (Deduction - Root Cause)
**Claim**: The bug is in `django/forms/models.py:86` where the condition `if fields and f.name not in fields:` treats an empty list as falsy, causing it to skip the field exclusion logic.

**Evidence**: 
- `django/forms/models.py:86` contains: `if fields and f.name not in fields:`
- In Python, empty list `[]` is falsy, so `if []` evaluates to `False`
- When `fields=[]`, the condition becomes `if [] and ...` → `False`, so no fields are skipped
- All fields get added to the returned dict instead of none

**Reasoning**: 
- The condition should be `if fields is not None and f.name not in fields:`
- This distinguishes between `fields=None` (default, include all) and `fields=[]` (include none)
- When `fields=[]`: `fields is not None` → `True`, so check `f.name not in []` → `True`, skip all fields ✓
- When `fields=None`: `fields is not None` → `False`, so don't skip any fields ✓  
- When `fields=['id']`: `fields is not None` → `True`, check `f.name not in ['id']`, skip fields not in list ✓

**Confidence**: Deduction - 98%

**Supporting code**:
- Other functions in the same file (`construct_instance:46`, `fields_for_model:151`) already use the correct pattern: `if fields is not None and f.name not in fields:`
- The `exclude` parameter correctly uses `if exclude and f.name in exclude:` because an empty exclude list `[]` should exclude nothing (opposite semantics)

## H₂ (Deduction - Secondary Bug Site)
**Claim**: The same bug exists at `django/forms/models.py:434` in the `_save_m2m` method.

**Evidence**: Line 434 contains identical buggy pattern: `if fields and f.name not in fields:`

**Reasoning**: While not tested by the current failing test, this would cause the same bug if a ModelForm is defined with `Meta.fields = []`. For consistency and correctness, both locations should be fixed.

**Confidence**: Deduction - 95%

## Craft gate loop

### Iteration 1: Draft + codex volley + apply

**Drafted fix**: Changed line 86 in `django/forms/models.py` from `if fields and f.name not in fields:` to `if fields is not None and f.name not in fields:` to properly handle empty list vs None.

**codex feedback**: 
- model_to_dict() change is correct for the failing test ✓
- Warned _save_m2m() line 434 change (also mentioned by recon) is behavior-changing without test coverage
- Recommended applying only the minimal fix for FAIL_TO_PASS

**Applied**: Line 86 fix only (minimal change for test requirement)

**Gate result**: ✅ PASS - All 143 tests passed including `test_modelform_subclassed_model`

**Resolution**: FAIL_TO_PASS test now passes. The fix correctly distinguishes `fields=None` (return all) from `fields=[]` (return empty dict) by using explicit None check instead of truthy check.

**Edit sites not applied**: Line 434 `_save_m2m()` — recon suggested for consistency but not required for FAIL_TO_PASS; codex warned of untested behavior change. Skipped per minimal-fix principle.

# Audit: django__django-11163

## FAIL_TO_PASS
- test_modelform_subclassed_model (model_forms.tests.ModelOneToOneFieldTests): **PASS** ✓

## PASS_TO_PASS regressions
None - all 143 tests passed.

## Pre-existing (not counted, confirmed against base capture)
None - the test that failed on base now passes.

## Patch details
```diff
diff --git a/django/forms/models.py b/django/forms/models.py
index d157c291ef..5edbbd376f 100644
--- a/django/forms/models.py
+++ b/django/forms/models.py
@@ -83,7 +83,7 @@ def model_to_dict(instance, fields=None, exclude=None):
     for f in chain(opts.concrete_fields, opts.private_fields, opts.many_to_many):
         if not getattr(f, 'editable', False):
             continue
-        if fields and f.name not in fields:
+        if fields is not None and f.name not in fields:
             continue
         if exclude and f.name in exclude:
             continue
```

The fix changes the truthy check `if fields` to an explicit None check `if fields is not None`, allowing `fields=[]` to be properly distinguished from `fields=None`. This causes `model_to_dict(instance, fields=[])` to correctly return an empty dict instead of all fields.

## Verdict
All FAIL_TO_PASS tests pass. Zero PASS_TO_PASS regressions. The patch is minimal, surgical, and solves the reported issue.

VERDICT: RESOLVED
RE-ENTER: none
