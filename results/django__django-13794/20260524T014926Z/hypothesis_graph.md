# Hypothesis graph: django__django-13794

## H0: Initial Observation (abduction)
**Date**: 2026-05-23
**Status**: Foundation
**Confidence**: 95% (deduction)

The tests fail because lazy proxy objects don't support arithmetic operations with other lazy proxies or regular values.

**Evidence**:
- `test_add08`: `'string' + lazy('lazy')` returns '' instead of 'stringlazy'
- `test_add09`: `lazy('string') + lazy('lazy')` returns '' instead of 'stringlazy'
- `test_lazy_add`: `lazy_4() + lazy_5()` raises `TypeError: unsupported operand type(s) for +: '__proxy__' and '__proxy__'`

**Failure modes**:
1. Template filter: Exception is caught, empty string returned
2. Direct operation: TypeError propagates

## H1: Root Cause - __promise__ doesn't force Promise arguments (deduction)
**Date**: 2026-05-23
**Status**: Active hypothesis
**Confidence**: 98% (deduction)

The `__promise__` class method in `django/utils/functional.py` (lines 130-137) creates wrappers for magic methods copied from result classes. These wrappers force evaluation of `self` (left operand) but pass arguments through unchanged. When an argument is a Promise proxy, the underlying method (e.g., `int.__add__`, `str.__add__`) receives a proxy object it doesn't understand.

**Code evidence**:
- `django/utils/functional.py:130-137` - `__promise__` implementation:
  ```python
  @classmethod
  def __promise__(cls, method_name):
      def __wrapper__(self, *args, **kw):
          res = func(*self.__args, **self.__kw)
          return getattr(res, method_name)(*args, **kw)
      return __wrapper__
  ```
  The `args` are passed directly to the underlying method without checking for Promise instances.

- `django/utils/functional.py:160-167` - Comparison operators handle this explicitly:
  ```python
  def __eq__(self, other):
      if isinstance(other, Promise):
          other = other.__cast()
      return self.__cast() == other
  ```
  But these are manually defined methods, not created via `__promise__`.

**Trace**:
1. `lazy_4() + lazy_5()` calls `lazy_4().__add__(lazy_5())`
2. `__add__` was created by `__prepare_class__()` using `__promise__('__add__')`
3. The wrapper evaluates `lazy_4` to get `4`
4. Then calls `int.__add__(lazy_5())` - but `lazy_5()` is still a proxy
5. `int.__add__` doesn't know how to handle `__proxy__`, raises TypeError

**Why template filter fails**:
- `django/template/defaultfilters.py:675-684` - `add` filter catches all exceptions:
  ```python
  def add(value, arg):
      try:
          return int(value) + int(arg)
      except (ValueError, TypeError):
          try:
              return value + arg  # This raises TypeError with proxies
          except Exception:
              return ''  # Returns empty string
  ```

**Fix**: Modify `__promise__` to force evaluation of Promise arguments before calling the underlying method.


## /craft gate loop

### Iteration 1
**Action**: Applied initial fix to `__promise__` method - modified wrapper to force evaluation of Promise arguments before calling underlying method, changed `func(*self.__args, **self.__kw)` to `self.__cast()` for consistency.

**Gate Result**: DIVERGENT (progress)
- test_lazy_add: PASS ✓
- test_add09: PASS ✓  
- test_add08: FAIL (returns '' instead of 'stringlazy')

**Codex Analysis**: The failure occurs because when evaluating `'string' + lazy_proxy`, Python calls `str.__add__('string', lazy_proxy)` first. When that fails, Python should call `lazy_proxy.__radd__('string')`, but `__radd__` doesn't exist on the proxy because `str` doesn't define it in its `__dict__`. The `__prepare_class__` method only creates wrappers for methods that exist in the result class.

### Iteration 2
**Action**: Added explicit `__radd__` method to handle reflected addition, placed alongside other explicit methods like `__eq__`, `__lt__`, and `__mod__`.

```python
def __radd__(self, other):
    return other + self.__cast()
```

**Gate Result**: CONVERGENT (GREEN) ✓
- test_lazy_add: PASS ✓
- test_add08: PASS ✓
- test_add09: PASS ✓

All FAIL_TO_PASS tests now pass. Gate is green.

**Final Diff**:
- Modified `__promise__` method to force evaluation of Promise arguments and use `self.__cast()` for consistency
- Added explicit `__radd__` method to handle reflected addition when the left operand is a non-Promise object

---

## /audit: Final Verification
**Date**: 2026-05-23

### FAIL_TO_PASS
- test_lazy_add (utils_tests.test_functional.FunctionalTests): **PASS** ✓
- test_add08 (template_tests.filter_tests.test_add.AddTests): **PASS** ✓
- test_add09 (template_tests.filter_tests.test_add.AddTests): **PASS** ✓

### PASS_TO_PASS regressions
None. All 24 PASS_TO_PASS tests remain passing.

### Pre-existing failures (not counted)
None. All previously failing tests are now passing.

### Gate output
```
Ran 27 tests in 0.007s
OK
```

**Contract fulfilled**: All FAIL_TO_PASS tests pass, zero PASS_TO_PASS regressions.

