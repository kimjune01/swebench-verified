# Hypothesis graph: django__django-15731

## Hypothesis H₀ (Abduction)
**Status**: Active
**Type**: Root cause identification
**Claim**: The test fails because `inspect.signature()` returns `(*args, **kwargs)` instead of the actual signature when called on manager methods like `Article.objects.bulk_create`.

### Evidence
- Test failure shows: `AssertionError: '(*args, **kwargs)' != '(objs, batch_size=None, ignore_conflicts=False, update_conflicts=False, update_fields=None, unique_fields=None)'`
- The wrapper function `manager_method` in `_get_queryset_methods` is defined with signature `(self, *args, **kwargs)`
- Only `__name__` and `__doc__` are manually copied from the original method

### Root Cause
In `django/db/models/manager.py` lines 83-91, the `create_method` function creates wrapper methods that delegate to QuerySet methods. The wrapper manually assigns `__name__` and `__doc__` but does not copy signature metadata that `inspect.signature()` needs (specifically the `__wrapped__` attribute).

### Fix
Replace manual metadata copying with `functools.wraps(method)` decorator, which automatically copies all necessary attributes including `__wrapped__`, enabling `inspect.signature()` to follow the wrapper chain to the original function's signature.

### Confidence
**Deduction - 98%**: Verified via Python testing that `functools.wraps` preserves signature information for `inspect.signature()` while manual `__name__`/`__doc__` assignment does not.


---
## Craft Gate Loop

### Iteration 1: Initial implementation

**Codex volley (pre-gate):**
- Proposed using `@functools.wraps(method)` decorator
- codex identified risk: `functools.wraps()` copies full `__dict__` including Django-specific attributes (`alters_data`, `queryset_only`) that weren't previously exposed on manager methods
- codex recommended minimal fix: manually set `manager_method.__wrapped__ = method` while preserving existing `__name__` and `__doc__` assignments
- This avoids behavior change while giving `inspect.signature()` the unwrap chain it needs

**Applied patch:**
```python
# django/db/models/manager.py line 89 (after __doc__ assignment)
manager_method.__wrapped__ = method
```

**Gate result:** ✅ PASS
- All 61 tests passed including `test_manager_method_signature`
- No regressions in PASS_TO_PASS tests

**Resolution:** RESOLVED - FAIL_TO_PASS test passes, no behavioral changes beyond signature introspection

---
## Audit: django__django-15731

### Patch verification
✅ Patch is live: `django/db/models/manager.py` (+1 line)

### Gate execution
Ran 61 tests via `/tmp/gate-django_django-15731`
- Result: OK (skipped=2)
- Duration: 0.052s

### FAIL_TO_PASS
- `test_manager_method_signature (basic.tests.ManagerTest)` → **PASS** ✅

### PASS_TO_PASS regressions
**None** — all 61 tests passed

### Pre-existing failures (confirmed against base capture)
**None** — 2 skipped tests are expected database feature skips:
- `test_emptyqs_distinct` (no can_distinct_on_fields support)
- `test_concurrent_delete_with_save` (no test_db_allows_multiple_connections)

### Applied fix
```python
# django/db/models/manager.py:89
manager_method.__wrapped__ = method
```

This minimal 1-line addition enables `inspect.signature()` to unwrap the manager method to the underlying QuerySet method signature, while preserving Django's existing `__name__` and `__doc__` assignment pattern (avoiding unintended exposure of QuerySet-specific attributes like `alters_data`).

VERDICT: RESOLVED
RE-ENTER: none
