# Hypothesis graph: django__django-14500

---

## H₁: check_replacements missing inverse logic (abduction → deduction)

**Status:** Active hypothesis  
**Reasoning mode:** Deduction (traced code paths)  
**Confidence:** 98%

### Observation
When unapplying squashed migration `0001_squashed_0002`, the test expects it to be removed from applied_migrations(), but it remains marked as applied.

### Code path analysis

1. **During apply (forward):**
   - `apply_migration` → `record_migration` (executor.py:218-223)
   - For squashed migrations: records all individual replaced migrations as applied
   - `check_replacements` runs (executor.py:264-280)
   - If all replaced migrations are applied, marks squashed migration as applied too

2. **During unapply (backward):**
   - `unapply_migration` (executor.py:245-262)
   - For squashed migrations: only marks replaced migrations as unapplied (lines 253-256)
   - Squashed migration itself is NOT marked as unapplied
   - `check_replacements` runs but only has forward logic (lines 275-277)
   - No inverse logic to mark squashed as unapplied when replaced are not all applied

### Root cause
Asymmetric logic in `check_replacements`:
- ✅ Forward: `if all_applied and key not in applied: record_applied(*key)`
- ❌ Backward: Missing `if not all_applied and key in applied: record_unapplied(*key)`

### Evidence
```python
# django/db/migrations/executor.py:253-256
if migration.replaces:
    for app_label, name in migration.replaces:
        self.recorder.record_unapplied(app_label, name)
    # BUG: squashed migration itself never marked as unapplied
```

```python
# django/db/migrations/executor.py:275-277
all_applied = all(m in applied for m in migration.replaces)
if all_applied and key not in applied:
    self.recorder.record_applied(*key)
    # MISSING: inverse case for unapply
```

### Proposed fix
Add to `check_replacements` after line 277:
```python
if not all_applied and key in applied:
    self.recorder.record_unapplied(*key)
```

### Supporting tests
- `test_apply_all_replaced_marks_replacement_as_applied` (line 613): confirms forward case works
- `test_migrate_marks_replacement_applied_even_if_it_did_nothing` (line 636): confirms check_replacements handles "already applied" scenario
- `test_migrate_marks_replacement_unapplied` (line 657): **FAILING** - expects inverse behavior

## Craft Phase - Gate Loop

### Iteration 1: Initial Fix

**Hypothesis**: Add inverse logic to `check_replacements` to mark squashed migrations as unapplied when all their replaced migrations are unapplied.

**Implementation**:
```python
elif all(m not in applied for m in migration.replaces) and key in applied:
    self.recorder.record_unapplied(*key)
```

**Volley with codex**: codex raised concern about the condition being too broad, potentially incorrectly marking squashed migrations as unapplied in fresh installs. However, analysis of the code showed that when a squashed migration is applied, the replaced migrations ARE recorded via `record_migration`, so the condition is actually safe.

**Gate Result**: ✅ **GREEN** - All 22 tests pass, including `test_migrate_marks_replacement_unapplied`.

**Resolution**: The fix is correct. The `check_replacements` method now has symmetric logic:
- Forward: If all replaced migrations are applied, mark squashed migration as applied
- Backward: If none of the replaced migrations are applied, mark squashed migration as unapplied

The fix addresses the root cause identified in recon: asymmetric logic in `check_replacements` that only handled the forward case.

---

## Audit Phase

### Patch verification
```diff
diff --git a/django/db/migrations/executor.py b/django/db/migrations/executor.py
index 57042a8690..7c81e58399 100644
--- a/django/db/migrations/executor.py
+++ b/django/db/migrations/executor.py
@@ -278,6 +278,8 @@ class MigrationExecutor:
             if all_applied and key not in applied:
                 self.recorder.record_applied(*key)
 
+            elif all(m not in applied for m in migration.replaces) and key in applied:
+                self.recorder.record_unapplied(*key)
     def detect_soft_applied(self, project_state, migration):
         """
         Test whether a migration has been implicitly applied - that the
```

### Gate results (22 tests)

**FAIL_TO_PASS:**
- `test_migrate_marks_replacement_unapplied` → **PASS** ✓

**PASS_TO_PASS regressions:**
- None

**Pre-existing failures (not counted):**
- None

**All 22 tests passed:**
- test_alter_id_type_with_fk → ok
- test_apply_all_replaced_marks_replacement_as_applied → ok
- test_atomic_operation_in_non_atomic_migration → ok
- test_custom_user → ok
- test_detect_soft_applied_add_field_manytomanyfield → ok
- test_empty_plan → ok
- test_migrate_marks_replacement_applied_even_if_it_did_nothing → ok
- test_migrate_marks_replacement_unapplied → ok ✓ (was FAIL_TO_PASS)
- test_migrations_applied_and_recorded_atomically → ok
- test_migrations_not_applied_on_deferred_sql_failure → ok
- test_mixed_plan_not_supported → ok
- test_non_atomic_migration → ok
- test_process_callback → ok
- test_run → ok
- test_run_with_squashed → ok
- test_soft_apply → ok
- test_unrelated_applied_migrations_mutate_state → ok
- test_unrelated_model_lookups_backwards → ok
- test_unrelated_model_lookups_forwards → ok
- test_backwards_nothing_to_do → ok
- test_minimize_rollbacks → ok
- test_minimize_rollbacks_branchy → ok

### Verdict

✅ **RESOLVED**: All FAIL_TO_PASS tests pass, zero regressions.

The craft patch correctly implements the inverse logic in `check_replacements`:
- When all replaced migrations are unapplied AND the squashed migration is marked applied, it now records the squashed migration as unapplied
- This mirrors the existing forward logic and maintains symmetry in the replacement tracking system

