# Hypothesis graph: django__django-16493

## H₀: Tests fail due to missing storage kwarg in deconstruct (abduction, 85%)

**Observation**: The test `test_deconstruction_storage_callable_default` expects `kwargs["storage"]` to contain `callable_default_storage`, but gets `KeyError: 'storage'`.

**Root cause**: `FileField.deconstruct()` at line 298 checks `if self.storage is not default_storage:` to decide whether to include storage kwarg. When a callable returns `default_storage`, the evaluated `self.storage` IS `default_storage` (identity check), so the condition fails and storage is omitted.

**Supporting evidence**:
- `django/db/models/fields/files.py:245`: `self._storage_callable = self.storage` (stores callable before evaluation)
- `django/db/models/fields/files.py:246`: `self.storage = self.storage()` (evaluates to `default_storage`)
- `django/db/models/fields/files.py:298`: `if self.storage is not default_storage:` (False when evaluated storage IS default_storage)
- Issue #31941 fix added `_storage_callable` preservation but didn't update the condition

**Edit site**: `django/db/models/fields/files.py` line 298: Change to `if hasattr(self, "_storage_callable") or self.storage is not default_storage:`

**Confidence**: 85% (abduction) — Code inspection clearly shows the bug, though not yet tested against gate.

## Gate Loop — Iteration 1

**Diff applied:**
```diff
--- a/django/db/models/fields/files.py
+++ b/django/db/models/fields/files.py
@@ -295,7 +295,7 @@ class FileField(Field):
     if kwargs.get("max_length") == 100:
         del kwargs["max_length"]
     kwargs["upload_to"] = self.upload_to
-    if self.storage is not default_storage:
+    if hasattr(self, "_storage_callable") or self.storage is not default_storage:
         kwargs["storage"] = getattr(self, "_storage_callable", self.storage)
     return name, path, args, kwargs
```

**codex pre-gate review:** Logically correct and minimal. Fixes the exact bug: callable storage preserved in deconstruct() even when evaluated result is default_storage. No existing behavior breaks.

**Gate result:** PASS — all 149 tests passed, including test_deconstruction_storage_callable_default

**Trajectory:** Convergent success (single iteration to green)

---

# Audit: django__django-16493

## FAIL_TO_PASS
- test_deconstruction_storage_callable_default (implied from "A callable that returns default_storage is not omitted when"): **PASS**

## PASS_TO_PASS regressions
None. All 149 tests in the suite passed.

## Pre-existing (not counted, confirmed against base capture)
None. The base capture showed all tests passing except for the FAIL_TO_PASS test.

## Kill report
Not applicable — all requirements met.

The patch correctly solves the issue: when `FileField.deconstruct()` evaluates a callable storage that returns `default_storage`, the condition now checks for `_storage_callable` first, ensuring the callable is preserved in kwargs even when the evaluated result matches `default_storage`.

VERDICT: RESOLVED
RE-ENTER: none
