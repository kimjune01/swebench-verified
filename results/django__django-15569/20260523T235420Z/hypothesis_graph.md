# Hypothesis graph: django__django-15569

## Hypothesis Node 1 - Initial Diagnosis

**Type**: Abduction → Deduction
**Timestamp**: Initial recon pass
**Status**: Active

### Observation
Two failing tests show that unregistered lookups remain in the cache:
1. `test_lookups_caching`: After unregistering "exactly" lookup, `field.get_lookups()` still contains it
2. `test_get_transforms`: After unregistering "my_transform", it's still returned instead of the default KeyTransformFactory

Error from test_lookups_caching:
```
AssertionError: 'exactly' unexpectedly found in {'in': ..., 'exactly': <class 'custom_lookups.tests.Exactly'>}
```

### Root Cause Analysis

**Localization**: `django/db/models/query_utils.py` lines 210-219

**Code Path**:
1. `get_lookups()` at line 166 is decorated with `@functools.lru_cache(maxsize=None)`
2. `register_lookup()` at line 201 calls `cls._clear_cached_lookups()` at line 207
3. `_unregister_lookup()` at line 210 does NOT call `cls._clear_cached_lookups()`

**Historical Context** (from git log):
- August 2015 (commit 534aaf56f4): `_unregister_lookup` added without caching
- August 2016 (commit 7aeb7390fc): Caching added via `@lru_cache`, `_clear_cached_lookups()` created and called from `register_lookup()`
- Bug: When caching was introduced, `_unregister_lookup()` was not updated to clear the cache

**Root Cause**: When `_unregister_lookup()` removes a lookup from `cls.class_lookups` dict, it doesn't invalidate the `@lru_cache` on `get_lookups()`. The cached result still contains the removed lookup.

**Confidence**: Deduction (98%) - The code path is clear, the historical context confirms this was an oversight when caching was added, and both test failures directly demonstrate the missing cache clear.

### Edit Site

**File**: `django/db/models/query_utils.py`
**Line**: After line 219 (after `del cls.class_lookups[lookup_name]`)
**Change**: Add `cls._clear_cached_lookups()` to mirror the behavior in `register_lookup()`

**Specific change needed**:
```python
@classmethod
def _unregister_lookup(cls, lookup, lookup_name=None):
    """
    Remove given lookup from cls lookups. For use in tests only as it's
    not thread-safe.
    """
    if lookup_name is None:
        lookup_name = lookup.lookup_name
    del cls.class_lookups[lookup_name]
    cls._clear_cached_lookups()  # <-- ADD THIS LINE
```

### Supporting Evidence

1. **query_utils.py:166-168**: `get_lookups()` is cached
   ```python
   @classmethod
   @functools.lru_cache(maxsize=None)
   def get_lookups(cls):
   ```

2. **query_utils.py:195-198**: `_clear_cached_lookups()` exists to clear the cache
   ```python
   @classmethod
   def _clear_cached_lookups(cls):
       for subclass in subclasses(cls):
           subclass.get_lookups.cache_clear()
   ```

3. **query_utils.py:207**: `register_lookup()` calls it
   ```python
   cls._clear_cached_lookups()
   ```

4. **query_utils.py:210-219**: `_unregister_lookup()` does not call it

### Rejected Hypotheses
None - the diagnosis is straightforward from code inspection and git history.

### Open Questions
None - the fix is clear and complete.


## Craft Gate Loop

### Iteration 1

**Drafted fix:** Added `cls._clear_cached_lookups()` call in `_unregister_lookup()` at line 220, mirroring the pattern in `register_lookup()`.

**Codex review (pre-gate):**
- Findings: None - the one-line cache clear is the right fix
- Missing: Only verification
- Breakage risk: Low - mirrors register_lookup() invalidation

**Applied diff:**
```python
@classmethod
def _unregister_lookup(cls, lookup, lookup_name=None):
    """
    Remove given lookup from cls lookups. For use in tests only as it's
    not thread-safe.
    """
    if lookup_name is None:
        lookup_name = lookup.lookup_name
    del cls.class_lookups[lookup_name]
    cls._clear_cached_lookups()  # ADDED
```

**Gate result:** ✓ PASS

Both FAIL_TO_PASS tests pass:
- test_lookups_caching (custom_lookups.tests.LookupTests) ... ok
- test_get_transforms (model_fields.test_jsonfield.TestMethods) ... ok

**Status:** RESOLVED in 1 iteration

---

## Audit Verification

**Timestamp**: Final verification pass
**Gate**: Full test suite (custom_lookups.tests, model_fields.test_jsonfield, schema.tests)

### Phase 1: Patch confirmation
```
django/db/models/query_utils.py | 1 +
1 file changed, 1 insertion(+)
```

Patch is live in the tree at line 220.

### Phase 2: Gate execution
Ran 290 tests in 1.119s - **OK (skipped=40)**

### Phase 3: Result classification

#### FAIL_TO_PASS (both required to pass)
- ✓ test_lookups_caching (custom_lookups.tests.LookupTests) - **PASS**
- ✓ test_get_transforms (model_fields.test_jsonfield.TestMethods) - **PASS**

#### PASS_TO_PASS regressions
**None** - All PASS_TO_PASS tests remain passing.

#### Pre-existing failures (not counted)
**None** - No new failures detected. All tests in the gate passed.

### Phase 4: Verdict

**Contract fulfilled:**
- All FAIL_TO_PASS tests now pass ✓
- Zero PASS_TO_PASS regressions ✓
- Full test suite clean ✓

The fix is minimal (one line), targeted (cache invalidation on unregister), and mirrors the existing pattern in `register_lookup()`. The patch resolves both failing tests without introducing any regressions.

**VERDICT**: RESOLVED
**RE-ENTER**: none
