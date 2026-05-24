# Hypothesis graph: django__django-14787

## Hypothesis H₀ (abduction, initial)

**Node type:** abduction  
**Confidence:** 95% (deduction - traced code path, verified with experiments)

The test fails because `method_decorator()` creates a `functools.partial` object to wrap the bound method (line 40 in `django/utils/decorators.py`), but this partial object lacks function attributes like `__name__`, `__module__`, `__qualname__`, etc. When a decorator uses `@wraps(func)` (as in the test), it tries to access these attributes on the partial object and gets `None` or `AttributeError`.

**Evidence:**
- Test failure: `AssertionError: None != 'method'` - the decorator receives a function without `__name__`
- `django/utils/decorators.py:40`: `bound_method = partial(method.__get__(self, type(self)))`
- Verified experimentally: `hasattr(partial(method.__get__(...)), '__name__')` returns `False`
- Verified fix: `update_wrapper(partial_obj, method)` successfully copies attributes to partial

**Root cause:**
After creating the partial object on line 40, the code immediately passes it to decorators (line 41-42) without first copying the original method's attributes. Decorators that use `functools.wraps()` expect the function parameter to have standard function attributes.

**Historical context:**
The partial was introduced in commit f434f5b84f7 to fix #29253, allowing decorators to set new attributes (which can't be set on bound method objects). This fix introduced the regression - bound methods have function attributes, but partial objects don't inherit them automatically.


## Craft gate loop

### Iteration 1: Initial fix

**Hypothesis**: Add `update_wrapper(bound_method, method)` after creating the partial object in `_multi_decorate` to copy function attributes from the original method.

**Implementation**: Added `update_wrapper(bound_method, method)` at line 41 in `django/utils/decorators.py`, immediately after `bound_method = partial(method.__get__(self, type(self)))`.

**codex review**: Directionally correct. `functools.partial` has a writable `__dict__`, so `update_wrapper` works and makes decorators using `@wraps(func)` see `__name__`, `__module__`, `__qualname__`, `__doc__`, and `__annotations__`. Behavioral change is minimal and desirable.

**Gate result**: ✅ PASS - all 21 tests passed including `test_wrapper_assignments`

**E-value**: convergent-success (FAIL_TO_PASS test now passes, no regressions)

**Resolution**: RESOLVED - the partial object now carries function metadata that decorators using `@wraps` can access.

---

# Audit: django__django-14787

## FAIL_TO_PASS
- test_wrapper_assignments (@method_decorator preserves wrapper assignments.): **PASS** ✓

## PASS_TO_PASS regressions
None — all 20 tests remain passing.

## Pre-existing (not counted, confirmed against base capture)
None

## Summary
The patch successfully resolved the issue by adding `update_wrapper(bound_method, method)` in `django/utils/decorators.py:_multi_decorate()`. This ensures wrapper assignments (`__name__`, `__module__`, etc.) are preserved when `@method_decorator` is applied.

**Fix:**
```python
bound_method = partial(method.__get__(self, type(self)))
update_wrapper(bound_method, method)  # ← Added this line
```

The test that was failing (`test_wrapper_assignments`) now passes, verifying that `func.__name__` correctly returns `'method'` instead of `None`.

All 21 tests pass with no regressions.

VERDICT: RESOLVED
RE-ENTER: none
