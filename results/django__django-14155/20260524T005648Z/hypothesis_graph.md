# Hypothesis graph: django__django-14155

## H1: ResolverMatch.__repr__ doesn't handle functools.partial (ACTIVE)
**Mode**: deduction  
**Confidence**: 99%

**Observation**: Three test failures in `tests/urlpatterns_reverse/tests.py`:
- `test_repr`: String values (url_name, route) missing quotes in repr output
- `test_repr_functools_partial` (3 sub-tests): Partial functions show as `func=functools.partial` instead of full representation with wrapped function and keyword arguments

**Root cause**: 
The `__repr__` method at `django/urls/resolvers.py:61-65` uses `self._func_path` (a string) which loses functools.partial information. Additionally, it doesn't quote string values.

**Evidence**:
- `django/urls/resolvers.py:62-64` — Uses `self._func_path` instead of `self.func`
- `django/urls/resolvers.py:48-53` — For partials, `_func_path` becomes just `"functools.partial"` or the wrapped function's path
- Test output shows: `func=functools.partial` vs expected: `func=functools.partial(<function empty_view at 0x...>, template_name='template.html')`

**Edit sites**:
- `django/urls/resolvers.py:61-65` — Modify `__repr__` to:
  1. Check if `self.func` is `isinstance(functools.partial)`
  2. Format partials with wrapped function and keywords
  3. Quote string values with `%r` format

**Status**: Proposed fix ready for /craft

## Craft Gate Loop

### Iteration 1: Draft and Apply Fix

**Hypothesis**: The fix requires modifying `ResolverMatch.__repr__()` to:
1. Check if `self.func` is a `functools.partial` instance
2. If yes, use `repr(self.func)` to get the full representation
3. If no, use `self._func_path` as before
4. Use `%r` format specifier for string values (`url_name`, `route`) and other parameters to ensure proper quoting

**Implementation**:
```python
def __repr__(self):
    if isinstance(self.func, functools.partial):
        func_repr = repr(self.func)
    else:
        func_repr = self._func_path
    return "ResolverMatch(func=%s, args=%r, kwargs=%r, url_name=%r, app_names=%r, namespaces=%r, route=%r)" % (
        func_repr, self.args, self.kwargs, self.url_name,
        self.app_names, self.namespaces, self.route,
    )
```

**Codex Review**: Clean pass. No blocking issues. The fix correctly handles:
- Quoted strings for `url_name` and `route` via `%r`
- Full `functools.partial` representation via `repr(self.func)`
- Both normal and wrapped partials via `isinstance` check

**Gate Result**: ✓ GREEN - All 95 tests passed, including all three FAIL_TO_PASS tests:
- `test_repr`
- `test_repr_functools_partial`
- `test_resolver_match_on_request`

**Status**: RESOLVED in 1 iteration.

## Audit: django__django-14155

**Patch confirmed**: `django/urls/resolvers.py` modified (6 insertions, 2 deletions)

**Gate execution**: All 95 tests passed in 0.355s

### FAIL_TO_PASS Results
- ✓ `test_repr (urlpatterns_reverse.tests.ResolverMatchTests)` — PASS
- ✓ `test_repr_functools_partial (urlpatterns_reverse.tests.ResolverMatchTests)` — PASS
- ✓ `test_resolver_match_on_request (urlpatterns_reverse.tests.ResolverMatchTests)` — PASS

All three FAIL_TO_PASS tests now pass.

### PASS_TO_PASS Regressions
None. All 92 PASS_TO_PASS tests remain passing.

### Pre-existing Failures
None detected in gate run.

### Verdict Analysis
The craft patch successfully:
1. Handles `functools.partial` instances by using `repr(self.func)` to preserve full representation
2. Quotes string values using `%r` format specifier for proper repr output
3. Passes all existing tests without introducing regressions

The fix is minimal, focused, and correctly addresses the root cause identified in H1.

