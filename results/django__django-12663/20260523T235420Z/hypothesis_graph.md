# Hypothesis graph: django__django-12663

## H1: Field.get_prep_value doesn't unwrap SimpleLazyObject (PRIMARY HYPOTHESIS)

**Status**: Active  
**Confidence**: Deduction - 95%  
**Reasoning mode**: Code trace from error site to root cause

### Observation
Test `test_subquery_filter_by_lazy` fails with:
```
TypeError: int() argument must be a string, a bytes-like object or a number, not 'SimpleLazyObject'
```

Stack trace shows:
1. `tests/expressions/tests.py:624` - filter call with SimpleLazyObject  
2. `django/db/models/lookups.py:74` - `get_prep_lookup` calls `self.lhs.output_field.get_prep_value(self.rhs)`
3. `django/db/models/fields/__init__.py:1772` - `IntegerField.get_prep_value` calls `int(value)` on SimpleLazyObject

### Root Cause
`Field.get_prep_value` (line 803-806 in `django/db/models/fields/__init__.py`) currently only unwraps `Promise` objects (lazy translation strings) but doesn't handle `SimpleLazyObject` or `LazyObject` instances.

```python
def get_prep_value(self, value):
    """Perform preliminary non-db specific value checks and conversions."""
    if isinstance(value, Promise):
        value = value._proxy____cast()
    return value  # SimpleLazyObject passes through unwrapped!
```

When SimpleLazyObject reaches `IntegerField.get_prep_value`, it tries `int(value)` which fails because Python's `int()` doesn't know how to unwrap the proxy.

### Supporting Evidence
- `django/db/models/fields/__init__.py:803-806` - Field.get_prep_value only handles Promise
- `django/db/models/fields/__init__.py:1772` - IntegerField.get_prep_value calls int(value)
- `django/utils/functional.py:356` - SimpleLazyObject is a LazyObject subclass with _wrapped attribute
- `django/utils/functional.py:234` - `empty` sentinel indicates uninitialized LazyObject

### Edit Sites
1. **django/db/models/fields/__init__.py:24** - Add `LazyObject` and `empty` to imports from django.utils.functional
2. **django/db/models/fields/__init__.py:803-806** - Update Field.get_prep_value to unwrap LazyObject instances:
   - Check `isinstance(value, LazyObject)`  
   - If `value._wrapped is empty`, call `value._setup()` to initialize
   - Return `value._wrapped`

### Regression Context
Introduced in commit 3543129822 "Refs #27149 -- Moved subquery expression resolving to Query". That commit changed how subquery RHS values are resolved but didn't account for SimpleLazyObject needing unwrapping before get_prep_value.


## Craft Implementation (Gate Loop)

### Iteration 1: Initial Fix Attempt (Field.get_prep_value)
Applied recon diagnosis to add LazyObject unwrapping in `Field.get_prep_value`:
- Added `LazyObject, empty` imports to `django/db/models/fields/__init__.py`
- Added unwrapping logic after Promise check in `get_prep_value`

**Gate result**: FAIL - Error changed from SimpleLazyObject to Manager instance
- Unwrapped the lazy object successfully
- But `IntegerField.get_prep_value` still failed with `int(<Manager instance>)`
- Model-to-PK conversion didn't happen

**codex feedback**: Correct that unwrapping alone insufficient. Model-to-PK conversion belongs in relation lookup normalization, not base Field class.

### Iteration 2: Move to get_normalized_value
Based on codex recommendation, moved fix to `django/db/models/fields/related_lookups.py`:
- Removed LazyObject handling from `Field.get_prep_value`
- Added LazyObject unwrapping to `get_normalized_value` before Model check
- Added `LazyObject, empty` imports to `related_lookups.py`

**Gate result**: FAIL - Still SimpleLazyObject error (unchanged from original)
- `get_normalized_value` was never called
- Test uses annotated IntegerField from Subquery, not a ForeignKey
- Lookup path: `Exact` -> `Lookup.get_prep_lookup()` -> `IntegerField.get_prep_value()`
- NOT: `RelatedExact` -> `RelatedLookupMixin.get_prep_lookup()` -> `get_normalized_value()`

**codex feedback**: Fix must be in `Lookup.get_prep_lookup()` for generic lookup path. Need both LazyObject unwrapping AND model-to-PK conversion before calling field prep.

### Iteration 3: Final Fix (Lookup.get_prep_lookup) ✓
Modified `django/db/models/lookups.py`:
- Added `LazyObject, empty` imports
- Extended `Lookup.get_prep_lookup()` to:
  1. Unwrap LazyObject instances (check `_wrapped is empty`, call `_setup()` if needed)
  2. Convert Model instances to their `pk` value
  3. Then call `output_field.get_prep_value(rhs)`

**Gate result**: PASS - All 138 tests pass including `test_subquery_filter_by_lazy`

**Final edit sites**:
1. `django/db/models/lookups.py` line 14: Added `LazyObject, empty` to imports
2. `django/db/models/lookups.py` lines 70-86: Modified `Lookup.get_prep_lookup()` to unwrap LazyObject and convert Model to pk
3. `django/db/models/fields/related_lookups.py` lines 1-2: Added `LazyObject, empty` imports (kept for relation lookup path)
4. `django/db/models/fields/related_lookups.py` lines 27-30: Added LazyObject unwrapping to `get_normalized_value` (defense-in-depth for relation lookups)

**Resolution**: The fix handles SimpleLazyObject wrapping model instances in filter values by unwrapping at the lookup prep stage (before field-specific prep) and converting model instances to their primary keys. This works for both annotated integer fields (via generic Lookup path) and relation fields (via RelatedLookupMixin path).

## Audit: django__django-12663

### FAIL_TO_PASS
- `test_subquery_filter_by_lazy (expressions.tests.BasicExpressionsTests)`: **PASS** ✓

### PASS_TO_PASS regressions
None

### Pre-existing (not counted, confirmed against base capture)
None

### Kill report
N/A — patch resolves the issue with no regressions

VERDICT: RESOLVED
RE-ENTER: none
