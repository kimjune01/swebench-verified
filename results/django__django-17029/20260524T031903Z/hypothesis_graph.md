# Hypothesis graph: django__django-17029

## H₀: Missing cache_clear() call (abduction)
**Status**: Proposed  
**Confidence**: 95% (deduction)  
**Mode**: Deduction

### Observation
Test `test_clear_cache` fails with:
```
AssertionError: 1 != 0
```
at line: `self.assertEqual(apps.get_swappable_settings_name.cache_info().currsize, 0)`

After calling `apps.clear_cache()`, the `get_swappable_settings_name` LRU cache still contains 1 item when it should be empty.

### Root Cause
The `Apps.clear_cache()` method at `django/apps/registry.py:370-385` clears the `get_models` cache (line 378) but does NOT clear the `get_swappable_settings_name` cache.

Both methods are decorated with `@functools.cache`:
- `get_models` (line ~230): `@functools.cache` decorator - cache IS cleared in clear_cache()
- `get_swappable_settings_name` (line 283-284): `@functools.cache` decorator - cache is NOT cleared

### Supporting Evidence
- `django/apps/registry.py:283` — `@functools.cache` decorates `get_swappable_settings_name`
- `django/apps/registry.py:378` — Only `self.get_models.cache_clear()` is called
- No call to `self.get_swappable_settings_name.cache_clear()` exists in `clear_cache()`

### Edit Site
`django/apps/registry.py` line 378-379: Add `self.get_swappable_settings_name.cache_clear()` call after `self.get_models.cache_clear()`.


## Gate Loop — Iteration 1

**Drafted fix:**
- Added `self.get_swappable_settings_name.cache_clear()` at line 379 in `django/apps/registry.py`
- Placement: immediately after `self.get_models.cache_clear()` (line 378)
- Rationale: Both methods are decorated with `@functools.cache` and both must be cleared

**codex volley:** Approved. No functional problems, correct placement, addresses root cause directly.

**Gate result:** ✅ PASS — All 44 tests passed, including `test_clear_cache`

**Trajectory:** Convergent success — FAIL_TO_PASS test now passes on first attempt.

**Resolution:** The fix is minimal, complete, and correct. Added the missing cache clear call following the existing pattern.


## Audit: django__django-17029

**Patch confirmed live:**
```
django/apps/registry.py | 1 insertion(+)
```

**Change:** Added `self.get_swappable_settings_name.cache_clear()` at line 379.

### FAIL_TO_PASS
- `test_clear_cache (apps.tests.AppsTests.test_clear_cache)`: **PASS** ✓

### PASS_TO_PASS regressions
None. All 43 PASS_TO_PASS tests remain passing.

### Pre-existing failures (not counted)
None. All tests that were passing on base remain passing with the patch.

### Gate Output
All 44 tests passed in 0.007s. The single FAIL_TO_PASS test now passes, and zero regressions introduced.

### Classification
- **All FAIL_TO_PASS tests pass:** Yes (1/1)
- **Zero PASS_TO_PASS regressions:** Yes (0 regressions)
- **Verdict:** RESOLVED
- **Route:** none (complete)

The fix correctly addresses the root cause by clearing the `get_swappable_settings_name` cache alongside `get_models.cache_clear()`, following the same pattern for cached methods in the registry.

VERDICT: RESOLVED
RE-ENTER: none
