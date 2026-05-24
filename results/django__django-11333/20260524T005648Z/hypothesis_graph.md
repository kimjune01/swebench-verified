# Hypothesis graph: django__django-11333

## H1: lru_cache caches on input parameter, not normalized value

**Type**: abduction → deduction
**Status**: active
**Confidence**: 99%

The `@functools.lru_cache` decorator on `get_resolver` (line 67) caches based on the input parameter `urlconf`. When called with `urlconf=None`, the cache key is `None`. When called with `urlconf='urlpatterns.path_urls'`, the cache key is `'urlpatterns.path_urls'`. 

Even though the function normalizes `None` to `settings.ROOT_URLCONF` on line 70, this normalization happens INSIDE the function body, AFTER the cache key has already been computed by the decorator.

**Evidence**:
- `django/urls/resolvers.py:67-71` - current implementation
- Test failure: two different URLResolver objects returned for logically equivalent calls
- lru_cache documentation: cache key is based on function arguments

**Fix**: Normalize `urlconf` parameter BEFORE the cached function is invoked, so both `get_resolver()` and `get_resolver(settings.ROOT_URLCONF)` use the same cache key.

## craft gate loop

### iteration 1: divergent (syntax error)
Applied initial fix with wrapper pattern to normalize urlconf before caching. Python script incorrectly stripped quotes from regex pattern, causing `RegexPattern(r^/)` instead of `RegexPattern(r'^/')`. Fixed with sed substitution.

### iteration 2: divergent (cache_clear missing)
Gate failed with `AttributeError: 'function' object has no attribute 'cache_clear'`. The `get_resolver` function is now a plain wrapper (not decorated with lru_cache), but `django/urls/base.py:95` calls `get_resolver.cache_clear()` to clear URL caches. Fixed by exposing cache methods from `_get_resolver`:
```python
get_resolver.cache_clear = _get_resolver.cache_clear
get_resolver.cache_info = _get_resolver.cache_info
```

### iteration 3: PASS
Gate green. All tests pass including `test_resolver_cache_default__root_urlconf`.

**Final fix:**
- Created `_get_resolver(urlconf)` with `@lru_cache` decorator (no default parameter)
- Changed `get_resolver(urlconf=None)` to a wrapper that normalizes `None` to `settings.ROOT_URLCONF` before calling `_get_resolver`
- Exposed cache methods (`cache_clear`, `cache_info`) from `_get_resolver` to maintain compatibility with `clear_url_caches()`

This ensures `get_resolver()` and `get_resolver(settings.ROOT_URLCONF)` use the same cache key, returning the same cached URLResolver instance as expected.

---

# Audit: django__django-11333

## FAIL_TO_PASS
- test_resolver_cache_default__root_urlconf (urlpatterns.test_resolvers.ResolverCacheTests): PASS ✅

## PASS_TO_PASS regressions
none

## Pre-existing (not counted, confirmed against base capture)
none

## Verdict
All FAIL_TO_PASS tests now pass. Zero PASS_TO_PASS regressions. The fix successfully resolved the caching issue by normalizing the urlconf parameter before the cached function is invoked.

VERDICT: RESOLVED
RE-ENTER: none
