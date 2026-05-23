# Hypothesis graph: django__django-11141

## Hypothesis Node 1 (H₁): Migration loader skips namespace packages due to obsolete __file__ check

**Type**: Deduction  
**Confidence**: 99%  
**Status**: Initial diagnosis

### Observation
The test `test_loading_namespace_package` fails with:
```
NodeNotFoundError: Node ('migrations', '0001_initial') not a valid node
```

The migration file exists at `tests/migrations/test_migrations_namespace_package/0001_initial.py` but is never loaded into the migration graph.

### Root Cause
In `django/db/migrations/loader.py` lines 87-91, the loader checks if `module.__file__` is None and skips the module:

```python
# Empty directories are namespaces.
# getattr() needed on PY36 and older (replace w/attribute access).
if getattr(module, '__file__', None) is None:
    self.unmigrated_apps.add(app_config.label)
    continue
```

Namespace packages (Python 3 implicit packages without `__init__.py`) don't have a `__file__` attribute but do have a `__path__` attribute.

### Why This Check Is Obsolete
1. Originally added in commit e1266e50b2 (#21015) to skip empty directories
2. At that time, migration discovery used `os.path.dirname(module.__file__)` and `os.listdir()` to find migrations
3. In commit 29150d5da8 (#23406), migration discovery was changed to use `pkgutil.iter_modules(module.__path__)`
4. `pkgutil.iter_modules()` works with namespace packages because they have `__path__`
5. Therefore, the `__file__` check is no longer needed

### Supporting Evidence
- Line 101: `pkgutil.iter_modules(module.__path__)` - uses `__path__`, not `__file__`
- Lines 93-95: Already check for `__path__` to distinguish packages from single-file modules
- `django/db/migrations/questioner.py` lines 48-54: Already handles namespace packages correctly by using `__path__` when `__file__` is None

### Edit Sites
- `django/db/migrations/loader.py` lines 87-91: Remove the `__file__` check and its comment


## craft gate loop

### Iteration 1: Initial fix (too broad)
**Action**: Removed obsolete `__file__` check (lines 87-91)  
**Codex volley**: Approved core fix but warned about empty namespace packages  
**Gate result**: DIVERGENT
- ✅ `test_loading_namespace_package` (FAIL_TO_PASS) now passes
- ❌ `test_load_empty_dir` (PASS_TO_PASS) regressed
**Analysis**: Fix was too broad - treated all namespace packages as migrated, including empty ones

### Iteration 2: Narrowed fix
**Codex guidance**: Check for migrations before deciding - reject only empty namespace packages  
**Action**: 
1. Moved `migration_names` computation before `migrated_apps.add()` 
2. Added check: if namespace package AND no migrations → unmigrated
3. Otherwise → migrated

**Final logic**:
```python
# Module is not a package (e.g. migrations.py).
if not hasattr(module, '__path__'):
    self.unmigrated_apps.add(app_config.label)
    continue
# Force a reload if it's already loaded (tests need this)
if was_loaded:
    reload(module)
migration_names = {
    name for _, name, is_pkg in pkgutil.iter_modules(module.__path__)
    if not is_pkg and name[0] not in '_~'
}
# Empty namespace packages (no __init__.py, no migrations) are unmigrated.
if getattr(module, '__file__', None) is None and not migration_names:
    self.unmigrated_apps.add(app_config.label)
    continue
self.migrated_apps.add(app_config.label)
```

**Gate result**: ✅ GREEN (all 25 tests pass)
- ✅ `test_loading_namespace_package` passes (namespace package with migrations loaded)
- ✅ `test_load_empty_dir` passes (empty namespace package treated as unmigrated)

**Resolution**: FAIL_TO_PASS tests pass, no PASS_TO_PASS regressions

---

# Audit: django__django-11141

## FAIL_TO_PASS
- test_loading_namespace_package (Migration directories without an __init__.py file are loaded.): **PASS** ✓

## PASS_TO_PASS regressions
None — all 24 tests remain passing.

## Pre-existing (not counted)
None — the only failure on base (test_loading_namespace_package) is now resolved.

## Summary
All FAIL_TO_PASS tests pass. Zero regressions. The patch successfully enables loading migration directories without `__init__.py` files (namespace packages) by ensuring `pkgutil.iter_modules()` is used for module discovery, which correctly handles both regular packages and namespace packages.

VERDICT: RESOLVED
RE-ENTER: none
