# Hypothesis graph: django__django-13810

## H₀: Initial observation (abduction)
**Timestamp:** 2026-05-23  
**Mode:** abduction  
**Claim:** The test `test_async_and_sync_middleware_chain_async_call` fails because when an async client calls `await self._middleware_chain(request)`, it receives a non-awaitable `HttpResponse` object instead of a coroutine, causing `TypeError: object HttpResponse can't be used in 'await' expression`.

**Evidence:**
- Test output shows: `TypeError: object HttpResponse can't be used in 'await' expression` at `django/core/handlers/base.py:148` in `get_response_async`
- Traceback: `response = await self._middleware_chain(request)` tries to await a synchronous return value

## H₁: Root cause - handler mutation before MiddlewareNotUsed check (deduction)
**Timestamp:** 2026-05-23  
**Mode:** deduction  
**Confidence:** 95%  
**Claim:** In `django/core/handlers/base.py:load_middleware()`, the `handler` variable is adapted (wrapped with `async_to_sync` or `sync_to_async`) BEFORE the middleware is instantiated. When `MiddlewareNotUsed` is raised during instantiation, the exception is caught and `continue` skips to the next middleware, but the adapted handler persists. Additionally, `handler_is_async` is not updated (lines 87-88 are skipped), creating a mismatch where the handler is sync-wrapped but the code believes it's still async.

**Evidence:**
- `django/core/handlers/base.py:54-57` - handler is adapted BEFORE middleware instantiation:
  ```python
  handler = self.adapt_method_mode(
      middleware_is_async, handler, handler_is_async,
      debug=settings.DEBUG, name='middleware %s' % middleware_path,
  )
  mw_instance = middleware(handler)
  ```
- `django/core/handlers/base.py:59-63` - MiddlewareNotUsed is caught and continues:
  ```python
  except MiddlewareNotUsed as exc:
      if settings.DEBUG:
          if str(exc):
              logger.debug('MiddlewareNotUsed(%r): %s', middleware_path, exc)
          else:
              logger.debug('MiddlewareNotUsed: %r', middleware_path)
      continue
  ```
- `django/core/handlers/base.py:87-88` - handler_is_async is only updated on success (these lines are SKIPPED when MiddlewareNotUsed triggers continue):
  ```python
  handler = convert_exception_to_response(mw_instance)
  handler_is_async = middleware_is_async
  ```

**Causal chain:**
1. First middleware in loop (MyMiddleware in reversed order): `middleware_is_async=False`, `handler_is_async=True`
2. `adapt_method_mode` wraps async handler with `async_to_sync`, making it sync
3. `MyMiddleware(handler)` raises `MiddlewareNotUsed`
4. `continue` executes, skipping lines 87-88
5. Second middleware (SyncAndAsyncMiddleware): handler is now sync, but `handler_is_async` is still `True`
6. Code incorrectly believes handler is async, doesn't re-adapt
7. Final `_middleware_chain` is a sync function
8. Async client tries to `await` it → TypeError

**Edit sites:**
- `django/core/handlers/base.py` lines 53-63: Move handler adaptation AFTER successful middleware instantiation, inside the try block after the middleware is created. This ensures that if `MiddlewareNotUsed` is raised, the handler remains unchanged.

**Alternative fix:** Restore the handler and handler_is_async values in the except block. But moving the adaptation after instantiation is cleaner as it avoids unnecessary work when the middleware won't be used.

## Craft iteration 1: Fix applied

**Change**: Modified `django/core/handlers/base.py` lines 54 and 58
- Changed `handler = self.adapt_method_mode(...)` to `adapted_handler = self.adapt_method_mode(...)`
- Changed `mw_instance = middleware(handler)` to `mw_instance = middleware(adapted_handler)`

**Rationale**: When `MiddlewareNotUsed` is raised during middleware instantiation, the adapted handler should not persist to the next iteration. Using a temporary variable `adapted_handler` prevents the state mismatch between the adapted handler and `handler_is_async` tracking variable.

**codex review**: Confirmed fix is correct - prevents skipped middleware from mutating handler, keeps handler and handler_is_async consistent.

**Gate result**: PASS ✓
- All 33 tests passed including `test_async_and_sync_middleware_chain_async_call`
- No regressions observed

**Status**: RESOLVED

## Audit: django__django-13810

**Timestamp:** 2026-05-23  
**Patch status:** Live (2 insertions, 2 deletions in django/core/handlers/base.py)

### FAIL_TO_PASS
- `test_async_and_sync_middleware_chain_async_call (middleware_exceptions.tests.MiddlewareNotUsedTests)`: **PASS** ✓ (was ERROR on base)

### PASS_TO_PASS regressions
None — all 32 PASS_TO_PASS tests still passing.

### Pre-existing failures (not counted)
None identified.

### Gate output
All 33 tests passed in 0.074s. Clean run.

### Verification
- The FAIL_TO_PASS test now passes (ERROR → PASS)
- Zero regressions introduced
- All PASS_TO_PASS tests remain green
- Fix successfully prevents handler mutation when MiddlewareNotUsed is raised

VERDICT: RESOLVED  
RE-ENTER: none
