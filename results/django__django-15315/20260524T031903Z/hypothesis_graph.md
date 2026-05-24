# Hypothesis graph: django__django-15315

## H₀: Initial diagnosis (abduction)
**Status**: Active
**Reasoning mode**: Deduction (95%)
**Claim**: Field.__hash__() includes mutable model attributes, causing hash to change when field is assigned to a model class.

### Evidence
- Test failure: `AssertionError: 8113426018888112013 != 4738423687416990223`
- `django/db/models/fields/__init__.py:544-550`: __hash__ includes `self.model._meta.app_label` and `self.model._meta.model_name`
- These are `None` when `not hasattr(self, 'model')`, but have values after assignment
- `django/db/models/fields/__init__.py:783`: `self.model = cls` is set in `contribute_to_class`, called when field is assigned to a model
- Commit 502e75f9ed added model info to __hash__ to distinguish inherited fields, but violated hash immutability

### Root cause
The __hash__ method returns a hash based on `(creation_counter, app_label, model_name)`, where app_label and model_name change from `None` to actual values when the field is assigned to a model class in `contribute_to_class()`. This violates Python's requirement that an object's hash must not change during its lifetime.

### Proposed fix
Revert __hash__ to only use `creation_counter`:
```python
def __hash__(self):
    return hash(self.creation_counter)
```

This allows hash collisions (fields with same creation_counter but different models will have same hash), but Python's equality check will still distinguish them correctly via __eq__.

### Supporting quotes
- `django/db/models/fields/__init__.py:544-550`:
```python
def __hash__(self):
    return hash((
        self.creation_counter,
        self.model._meta.app_label if hasattr(self, 'model') else None,
        self.model._meta.model_name if hasattr(self, 'model') else None,
    ))
```

- `django/db/models/fields/__init__.py:517-523`:
```python
def __eq__(self, other):
    # Needed for @total_ordering
    if isinstance(other, Field):
        return (
            self.creation_counter == other.creation_counter and
            getattr(self, 'model', None) == getattr(other, 'model', None)
        )
    return NotImplemented
```


## Craft iteration 1 (RESOLVED)
**Trajectory**: Convergent — resolved on first gate attempt
**Action**: Applied minimal fix from H₀

### Fix applied
Changed `django/db/models/fields/__init__.py:544-550` from:
```python
def __hash__(self):
    return hash((
        self.creation_counter,
        self.model._meta.app_label if hasattr(self, 'model') else None,
        self.model._meta.model_name if hasattr(self, 'model') else None,
    ))
```

To:
```python
def __hash__(self):
    return hash(self.creation_counter)
```

### Codex review (pre-gate)
- **Correctness**: No issues — fix preserves Python's hash invariant (equal objects have equal hashes)
- **Behavior change**: Fields with same `creation_counter` but different `model` now collide in hash tables (acceptable — `__eq__` still distinguishes them)
- **Suggestion**: Add comment to prevent re-introducing model metadata (deferred as out of scope)

### Gate result
✅ **PASS** — All FAIL_TO_PASS tests now pass (1/1)
- `test_hash_immutability (model_fields.tests.BasicFieldTests)`: ✅ PASS
- Total: 34 tests, 0 failures

**Resolution**: The fix correctly addresses the hash immutability violation. By hashing only `creation_counter` (an immutable field attribute), the hash remains constant throughout the field's lifetime, even when the field is assigned to a model class via `contribute_to_class()`.

---

## Audit: django__django-15315

### FAIL_TO_PASS
- `test_hash_immutability (model_fields.tests.BasicFieldTests)`: ✅ PASS

### PASS_TO_PASS regressions
None — all 34 tests in the suite passed.

### Pre-existing failures (not counted, confirmed against base capture)
None

### Verdict classification
- All FAIL_TO_PASS pass: ✅ (1/1)
- Zero PASS_TO_PASS regressions: ✅ (0 regressions)
- Gate output: 34 tests ran, all passed

The craft patch successfully resolves the hash immutability issue by simplifying `Field.__hash__()` to only use `self.creation_counter`, removing the dependency on mutable `self.model` attributes. No regressions introduced.

