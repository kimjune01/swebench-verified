# Hypothesis graph: django__django-13344

## Hypothesis Node: Missing _async_check() calls in middleware __init__
**Type:** Root cause (deduction)
**Confidence:** 95%

**Symptom:**
Tests fail with `AssertionError: False is not True` when checking `asyncio.iscoroutinefunction(middleware_instance)` for middlewares instantiated with async `get_response`.

**Root cause:**
Four middlewares override `__init__()` but fail to call either `super().__init__()` or `self._async_check()`:
1. `UpdateCacheMiddleware` (django/middleware/cache.py:65)
2. `FetchFromCacheMiddleware` (django/middleware/cache.py:132)
3. `CacheMiddleware` (django/middleware/cache.py:168)
4. `SecurityMiddleware` (django/middleware/security.py:10)

**Evidence:**
- `MiddlewareMixin.__init__()` calls `self._async_check()` at line django/utils/deprecation.py:109
- `_async_check()` sets `self._is_coroutine = asyncio.coroutines._is_coroutine` when `get_response` is a coroutine function (line 111-117)
- This marker is required for `asyncio.iscoroutinefunction()` to recognize the instance as a coroutine function
- `SessionMiddleware` passes the test because it explicitly calls `self._async_check()` in its `__init__()` (django/contrib/sessions/middleware.py:18)
- `RedirectFallbackMiddleware` passes because it calls `super().__init__(get_response)` (django/contrib/redirects/middleware.py:20)

**Traceability:**
- Git commit fc0fa72ff4 added async support and updated SessionMiddleware to call `_async_check()`
- Cache middlewares and SecurityMiddleware were not updated in that commit

**Fix specification:**
Add `self._async_check()` call after setting `self.get_response` in:
1. `UpdateCacheMiddleware.__init__()` after line 71
2. `FetchFromCacheMiddleware.__init__()` after line 137
3. `CacheMiddleware.__init__()` after line 173
4. `SecurityMiddleware.__init__()` after line 23


## /craft gate-loop: iteration 1

**Pre-gate codex volley:** Approved. codex confirmed the fix is minimal and correct — adding `self._async_check()` after `self.get_response = get_response` in four middlewares restores the coroutine marker behavior without breaking existing initialization.

**Edits applied:**
- `django/middleware/cache.py` line 74: Added `self._async_check()` in `UpdateCacheMiddleware.__init__()`
- `django/middleware/cache.py` line 136: Added `self._async_check()` in `FetchFromCacheMiddleware.__init__()`
- `django/middleware/cache.py` line 178: Added `self._async_check()` in `CacheMiddleware.__init__()`
- `django/middleware/security.py` line 24: Added `self._async_check()` in `SecurityMiddleware.__init__()`

**Gate result:** ✅ PASS — all 487 tests OK, including both FAIL_TO_PASS tests:
- `test_coroutine (deprecation.test_middleware_mixin.MiddlewareMixinTests) ... ok`
- `test_deprecation (deprecation.test_middleware_mixin.MiddlewareMixinTests) ... ok`

**Trajectory:** convergent-green (first gate run, all targets pass).

**Outcome:** RESOLVED — recon diagnosis was correct, fix is minimal and complete.


## /audit: Final Verification

**Patch confirmation:** ✅ Live (4 insertions across 2 files)

**Full gate execution:** 487 tests run, OK (skipped=117)

### FAIL_TO_PASS Results
- `test_coroutine (deprecation.test_middleware_mixin.MiddlewareMixinTests)` - **PASS** ✓
- `test_deprecation (deprecation.test_middleware_mixin.MiddlewareMixinTests)` - **PASS** ✓

### PASS_TO_PASS Regressions
None — all PASS_TO_PASS tests remain passing, including:
- All cache.tests.PrefixedCacheUtils tests (6/6)
- All cache.tests.TestMakeTemplateFragmentKey tests (6/6)
- All cache.tests.TestWithTemplateResponse tests (3/3)
- All cache.tests.DummyCacheTests tests (23/23)
- All other cache and deprecation tests (449/449)

### Pre-existing failures
None — no failures in baseline capture or current gate run.

### Audit verdict
All FAIL_TO_PASS tests now pass. Zero PASS_TO_PASS regressions. The fix is complete and correct.
