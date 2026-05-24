# Hypothesis graph: django__django-15277

## Hypothesis H0 (recon iteration 1)
**Status:** Active
**Type:** Deduction
**Confidence:** 99%

### Failure summary
The test `test_output_field_does_not_create_broken_validators` fails with:
```
TypeError: '>' not supported between instances of 'int' and 'NoneType'
```
at `django/core/validators.py:391` in `MaxLengthValidator.compare()`.

### Root cause
When `Value._resolve_output_field()` creates a `CharField` for string values, it calls `CharField()` with no arguments. This sets `max_length=None` (the Field base class default). However, `CharField.__init__` (line 1013) **unconditionally** adds `MaxLengthValidator(self.max_length)`, creating a validator with `limit_value=None`.

When this validator runs via `field.clean()`, it:
1. Calls `clean(value)` → returns `len(value)` (an int)
2. Calls `compare(len(value), None)` → tries `int > None` → TypeError

### Supporting evidence
- `django/db/models/expressions.py:785-786`: `Value._resolve_output_field()` returns `fields.CharField()` for strings
- `django/db/models/fields/__init__.py:1013`: CharField unconditionally adds `validators.MaxLengthValidator(self.max_length)`
- `django/db/models/fields/__init__.py:2324-2325`: BinaryField uses the CORRECT pattern: `if self.max_length is not None: self.validators.append(...)`
- `django/core/validators.py:391`: MaxLengthValidator.compare does `return a > b`, which fails when b is None

### Edit sites
- `django/db/models/fields/__init__.py` line 1013: Wrap the `validators.append(...)` in a conditional check `if self.max_length is not None:`

### Precedent
BinaryField already uses this pattern (line 2324-2325), so this is consistent with existing Django code.

## Gate Loop (craft)

### Iteration 1
**Action**: Applied conditional guard to CharField.__init__ (django/db/models/fields/__init__.py:1013)
- Changed from unconditional `self.validators.append(validators.MaxLengthValidator(self.max_length))`
- To conditional: `if self.max_length is not None: self.validators.append(validators.MaxLengthValidator(self.max_length))`
- Matches BinaryField pattern at line 2324-2325

**codex review**: Confirmed fix is correct and scoped. Notes behavior change is narrow (only affects CharField with max_length=None, which is invalid but used by Value._resolve_output_field()).

**Gate result**: ✓ PASS
- All 163 tests passed
- `test_output_field_does_not_create_broken_validators` now passes
- `test_raise_empty_expressionlist` passes
- No regressions

**Status**: RESOLVED

---

# Audit: django__django-15277

## FAIL_TO_PASS
- test_output_field_does_not_create_broken_validators (expressions.tests.ValueTests): **PASS** ✓
- test_raise_empty_expressionlist (expressions.tests.ValueTests): **PASS** ✓

## PASS_TO_PASS regressions
None — all 163 tests passed.

## Pre-existing (not counted, confirmed against base capture)
- test_mixed_comparisons1 (expressions.tests.FTimeDeltaTests): expected failure (was also expected failure on base)

## Summary
The craft patch successfully resolves the issue:
- Modified `django/db/models/fields/__init__.py:1013` to add conditional guard `if self.max_length is not None:` before appending `MaxLengthValidator`
- This prevents `TypeError: '>' not supported between instances of 'int' and 'NoneType'` when Value._resolve_output_field() creates a CharField with max_length=None
- All FAIL_TO_PASS tests now pass
- Zero PASS_TO_PASS regressions
- Follows existing Django pattern from BinaryField (line 2324-2325)

VERDICT: RESOLVED
RE-ENTER: none
