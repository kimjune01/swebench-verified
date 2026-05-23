# Hypothesis graph: django__django-11820

## H0: Initial failure observation (abduction, 90%)
The tests fail because:
1. `test_ordering_pointing_to_related_model_pk` expects no errors for `parent__pk` but gets models.E015
2. `test_ordering_pointing_multiple_times_to_model_fields` expects E015 for `parent__field1__field2` but gets no error

Error message for test 1: "'ordering' refers to the nonexistent field, related field, or lookup 'parent__pk'."

## H1: Root cause - 'pk' alias not handled in related field traversal (deduction, 95%)

**Location**: `django/db/models/base.py` lines 1706-1724

**Evidence**:
```python
# Line 1706-1724: Related fields validation loop
for field in related_fields:
    _cls = cls
    fld = None
    for part in field.split(LOOKUP_SEP):
        try:
            fld = _cls._meta.get_field(part)  # Line 1711: Fails for 'pk'
            if fld.is_relation:
                _cls = fld.get_path_info()[-1].to_opts.model
        except (FieldDoesNotExist, AttributeError):
            if fld is None or fld.get_transform(part) is None:
                errors.append(checks.Error(..., id='models.E015'))
```

**Bug 1** (causes test_ordering_pointing_to_related_model_pk failure):
- When processing `parent__pk`, the loop processes 'parent' successfully (ForeignKey), then tries `_cls._meta.get_field('pk')` on the Parent model
- 'pk' is an alias, not an actual field, so `get_field('pk')` raises FieldDoesNotExist
- The except handler checks `fld.get_transform('pk')` which returns None (ForeignKey doesn't have a 'pk' transform)
- E015 error is incorrectly raised for valid `parent__pk` reference

**Bug 2** (causes test_ordering_pointing_multiple_times_to_model_fields failure):
- When processing `parent__field1__field2`:
  - 'parent': ForeignKey, is_relation=True, _cls becomes Parent model
  - 'field1': CharField on Parent, is_relation=False, **_cls stays as Parent** (not updated)
  - 'field2': Calls `_cls._meta.get_field('field2')` on Parent model, which succeeds because Parent has field2
- No error raised, but should raise E015 because field1 (CharField) is not a relation, so field2 cannot be traversed as a model field

**Fix needed**:
1. Handle 'pk' specially - it's always valid when referencing a model's primary key
2. When a field is not a relation, subsequent parts must be validated as transforms/lookups on that field, not as fields on the current model

**Confidence**: Deduction - 95% (traced through code execution path, confirmed by test failure messages)

**Edit sites**:
- `django/db/models/base.py` lines 1706-1724: Modify the related fields validation loop to:
  1. Check if `part == 'pk'` and handle it as a valid alias
  2. After getting a non-relation field, validate remaining parts as transforms rather than model fields


## Gate Loop - Craft Iteration 1

**Drafted fix:**
- Added check for non-relation fields: when `fld` is not a relation, subsequent parts must be transforms
- Added 'pk' alias resolution: `if part == 'pk': fld = _cls._meta.pk`
- Added break after error to avoid duplicate errors

**Codex feedback (volley 1):**
- Original draft had `part == 'pk'` in exception handler, too broad (would allow `field1__pk`)
- Better to resolve 'pk' before calling `get_field()` using `_cls._meta.pk`
- Need to break after adding error

**Revised fix:**
Applied codex's suggested structure:
1. Check if previous field is non-relation → validate as transform
2. Before calling `get_field()`, check if `part == 'pk'` → resolve to `_cls._meta.pk`
3. Break after appending error to avoid duplicates

**Gate result:** ✅ PASS
- test_ordering_pointing_to_related_model_pk: PASS
- test_ordering_pointing_multiple_times_to_model_fields: PASS
- All 65 tests passing

**Trajectory:** Convergent-success (green gate on first attempt after codex review)

## Audit Report

### FAIL_TO_PASS
- `test_ordering_pointing_multiple_times_to_model_fields`: **PASS** ✓
- `test_ordering_pointing_to_related_model_pk`: **PASS** ✓

### PASS_TO_PASS regressions
**None** - all 65 tests passed (2 skipped)

### Pre-existing failures (not counted)
**None** - clean gate run

### Patch Stats
- `django/db/models/base.py`: 13 insertions, 1 deletion

### Final Status
All FAIL_TO_PASS tests now pass. Zero regressions introduced. Full contract satisfied.

