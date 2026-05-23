# Hypothesis graph: django__django-13297

## Hypothesis Node: H1 (Initial Diagnosis)

**Type**: Abduction → Deduction  
**Status**: Active  
**Timestamp**: 2026-05-22

### Observation
Test `test_template_params_filtering` fails with:
```
sqlite3.InterfaceError: Error binding parameter 0 - probably unsupported type.
```

Stack trace shows:
- `ArtistView.as_view()(request, artist_name=artist.name)` called
- `TemplateView.get()` wraps kwargs via `_wrap_url_kwargs_with_deprecation_warning(kwargs)`
- `get_context_data(*, artist_name, **kwargs)` receives wrapped `artist_name`
- `Artist.objects.get(name=artist_name)` fails because `artist_name` is SimpleLazyObject, not string

### Root Cause
**Location**: `django/views/generic/base.py:159-163, 167-181`

The deprecation mechanism in `TemplateView.get()` wraps **all** URL kwargs in `SimpleLazyObject` **before** calling `get_context_data()`. This is too early because:

1. The intent (per commit 4ed534758c) was to warn when URL kwargs are accessed **in templates**
2. But wrapping happens before `get_context_data()`, so user code that consumes kwargs (via explicit parameters like `artist_name`) receives SimpleLazyObject instances
3. These can't be used with database operations (SQLite, etc.) that expect concrete types

**Evidence**:
- `django/views/generic/base.py:162`: `context_kwargs = _wrap_url_kwargs_with_deprecation_warning(kwargs)`
- `django/views/generic/base.py:172-180`: wraps each value with `@SimpleLazyObject` decorator
- Test shows: `get_context_data(*, artist_name, **kwargs)` filters `artist_name` from context, but it's already wrapped

**Confidence**: Deduction — 98%  
(Traced code path from test through TemplateView.get() to wrapping function; reproduced failure; identified exact wrapping site)

### Proposed Fix
Move wrapping to **after** `get_context_data()` returns:
1. Pass unwrapped kwargs to `get_context_data()`
2. After receiving the returned context, wrap only values whose keys:
   - Were in the original URL kwargs
   - Still exist in the returned context
3. This way, kwargs consumed by `get_context_data()` (filtered out) won't be wrapped

### Edit Sites
1. `django/views/generic/base.py:159-163` — `TemplateView.get()` method
   - Change wrapping to happen after `get_context_data()` returns
   
2. `django/views/generic/base.py:167-181` — modify `_wrap_url_kwargs_with_deprecation_warning()` or create new function
   - Accept both url_kwargs and returned context
   - Wrap only url_kwargs keys that exist in returned context

### Competing Hypotheses
None — the code path is clear and deterministic.

### Rejected Hypotheses
None yet.


## Gate Loop - Iteration 1

**Action**: Applied fix to defer wrapping of URL kwargs until after `get_context_data()` returns.

**Changes**:
- Modified `TemplateView.get()` to call `get_context_data(**kwargs)` with unwrapped kwargs
- Changed `_wrap_url_kwargs_with_deprecation_warning()` to accept both `url_kwargs` and `context`, wrapping only URL kwargs that exist in the returned context
- Signature changed from returning a new dict to mutating the context dict in-place

**Key insight**: By wrapping only kwargs that survived into the final context (with `if key not in context: continue`), we avoid wrapping values that were explicitly consumed by `get_context_data()` parameter signatures (like `artist_name` in the test).

**Codex feedback**: Initial draft had critical indentation bug - `context[key] = access_value` was inside the function definition. Fixed to proper indentation at function scope.

**Gate result**: ✅ GREEN - All 59 tests pass, including `test_template_params_filtering`

**Evidence**: The fix correctly allows URL kwargs consumed by `get_context_data()` parameters to be used as normal values (not SimpleLazyObject), while still wrapping kwargs that reach the template context to emit deprecation warnings.


## Audit - Iteration 1

**Timestamp**: 2026-05-22

### FAIL_TO_PASS
- `test_template_params_filtering (generic_views.test_base.DeprecationTests)`: ✅ PASS

### PASS_TO_PASS regressions
None. All 59 tests passed.

### Pre-existing failures (not counted)
None applicable.

### Gate output
```
Ran 59 tests in 3.059s

OK
```

All expected tests passed:
- ✅ test_get_context_data_super
- ✅ test_object_at_custom_name_in_context_data
- ✅ test_object_in_get_context_data
- ✅ test_overwrite_queryset
- ✅ test_use_queryset_from_view
- ✅ test_template_mixin_without_template
- ✅ test_args_kwargs_request_on_self
- ✅ test_calling_more_than_once
- ✅ test_class_attributes
- ✅ test_direct_instantiation
- ✅ test_dispatch_decoration
- (... and 48 more)

### Verdict
The craft patch fully resolves the issue:
- The FAIL_TO_PASS test now passes (was ERROR on base, now ok)
- Zero regressions introduced
- All PASS_TO_PASS tests remain green

The fix correctly defers SimpleLazyObject wrapping until after `get_context_data()` returns, allowing user code to consume URL kwargs as concrete values while still emitting deprecation warnings for kwargs that reach the template context.
