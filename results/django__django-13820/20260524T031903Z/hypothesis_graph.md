# Hypothesis graph: django__django-13820

## H₀: Overly broad namespace package check
**Type**: Abduction → Deduction
**Status**: Active hypothesis

### Observation
Test `test_loading_package_without__file__` fails with:
```
AssertionError: Element counts were not equal:
First has 0, Second has 2:  '0001_initial', '0002_second'
```

The test deletes `__file__` from `migrations.test_migrations` module (simulating frozen Python environment), then calls `loader.load_disk()`. Expected 2 migrations, found 0.

### Root cause
`django/db/migrations/loader.py:93` checks `if getattr(module, '__file__', None) is None:` to skip namespace packages. This is too broad:
- Namespace packages: no `__file__`, `__path__` is custom iterable (NOT a list)
- Regular packages in frozen environments: no `__file__`, `__path__` IS a list
- Regular packages in normal environments: has `__file__`, `__path__` is a list

Current check conflates namespace packages with regular packages in frozen environments.

### Supporting evidence
- `django/db/migrations/loader.py:93-95`: Comment says "Empty directories are namespaces" but check only verifies `__file__` absence
- `tests/migrations/test_migrations/`: Regular package with `__init__.py`, should work without `__file__`
- `tests/migrations/test_migrations_namespace_package/`: No `__init__.py`, should be rejected (no changes needed for this case)
- Python docs: "Namespace packages do not use an ordinary list for their __path__ attribute. They instead use a custom iterable type"
- `git show ff55adbd0d`: Prior attempt allowed namespace packages, was reverted - intent is to block namespace packages, not frozen regular packages

### Edit site
`django/db/migrations/loader.py:93`
Change from:
```python
if getattr(module, '__file__', None) is None:
```
To:
```python
if getattr(module, '__file__', None) is None and not isinstance(getattr(module, '__path__', None), list):
```

This preserves namespace package rejection while allowing regular packages in frozen environments (where `__path__` is a list).

**Confidence**: Deduction, 95%

## Craft gate-loop

### Iteration 1
**Hypothesis**: Line 93 namespace package check is too broad — it rejects frozen regular packages that have list `__path__`.

**Change**: Modified `django/db/migrations/loader.py:93` from:
```python
if getattr(module, '__file__', None) is None:
```
to:
```python
if getattr(module, '__file__', None) is None and not isinstance(getattr(module, '__path__', None), list):
```

**Gate result**: ✓ PASS — All 26 tests passed
- `test_loading_package_without__file__` now passes (FAIL_TO_PASS)
- `test_loading_namespace_package` still passes (namespace packages still correctly rejected)

**Trajectory**: Convergent (resolution)

**Codex notes**: Raised concerns about line length and whether non-list `__path__` might exist for regular packages, but the gate confirms the fix is correct for Django's supported scenarios.

---

## Audit: django__django-13820

### FAIL_TO_PASS
- `test_loading_package_without__file__ (migrations.test_loader.LoaderTests)`: **PASS** ✓

### PASS_TO_PASS regressions
None. All PASS_TO_PASS tests continue to pass.

### Pre-existing failures (not counted)
None.

### Patch verification
```diff
diff --git a/django/db/migrations/loader.py b/django/db/migrations/loader.py
index 95a5062ec9..5e51194bbd 100644
--- a/django/db/migrations/loader.py
+++ b/django/db/migrations/loader.py
@@ -90,7 +90,7 @@ class MigrationLoader:
             else:
                 # Empty directories are namespaces.
                 # getattr() needed on PY36 and older (replace w/attribute access).
-                if getattr(module, '__file__', None) is None:
+                if getattr(module, '__file__', None) is None and not isinstance(getattr(module, '__path__', None), list):
                     self.unmigrated_apps.add(app_config.label)
                     continue
                 # Module is not a package (e.g. migrations.py).
```

### Gate output summary
Ran 26 tests in 0.103s — **ALL PASSED**

Key results:
- Target test `test_loading_package_without__file__` now passes (was FAIL on base)
- Namespace package test `test_loading_namespace_package` still passes (namespace packages still correctly rejected)
- All other loader tests pass without regression

### Analysis
The fix correctly distinguishes:
1. **Namespace packages** (no `__file__`, `__path__` not a list) → rejected
2. **Regular packages in frozen environments** (no `__file__`, `__path__` is a list) → accepted
3. **Normal packages** (has `__file__`) → accepted

The additional condition `and not isinstance(getattr(module, '__path__', None), list)` narrows the rejection logic to only true namespace packages, while allowing frozen regular packages (the test case) to proceed.

VERDICT: RESOLVED
RE-ENTER: none
