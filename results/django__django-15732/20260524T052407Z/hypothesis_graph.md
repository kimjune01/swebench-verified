# Hypothesis graph: django__django-15732

## H₀: Initial observation (abduction)
The test `test_remove_unique_together_on_unique_field` fails with:
```
ValueError: Found wrong number (2) of constraints for test_rutouf_pony(name)
```

Raised at: `django/db/backends/base/schema.py:572` in `_delete_composed_index`

The test creates a model with a field having both `unique=True` AND `unique_together={("name",)}`, creating two unique constraints:
1. `test_rutouf_pony_name_key` (field-level, database-generated name)
2. `test_rutouf_pony_name_694f3b9f_uniq` (unique_together, Django-generated name with `_uniq` suffix)

When removing the unique_together via `AlterUniqueTogether("Pony", set())`, it should delete only constraint #2, leaving #1 intact. Instead, it errors because it finds 2 constraints when expecting exactly 1.


## H₁: Root cause analysis (deduction)

**Code path:**
1. `AlterUniqueTogether.database_forwards` (`django/db/migrations/operations/models.py:565`)
2. → `alter_unique_together` (`django/db/backends/base/schema.py:520-537`)
3. → `_delete_composed_index` (`django/db/backends/base/schema.py:559-580`)

**Root cause in `_delete_composed_index` (lines 559-580):**

The method finds ALL constraints matching the columns and type (via `_constraint_names`), then enforces `len(constraint_names) == 1`:

```python
constraint_names = self._constraint_names(
    model,
    columns,
    exclude=meta_constraint_names | meta_index_names,
    **constraint_kwargs,  # {"unique": True} for unique_together
)
if len(constraint_names) != 1:
    raise ValueError(...)  # ← FAILS HERE when 2 constraints found
```

When a field has both `unique=True` and is in `unique_together`, two constraints exist:
1. Field-level unique (database-named, e.g., `{table}_{column}_key` in PostgreSQL)
2. unique_together constraint (Django-named: `{table}_{columns}_{hash}_uniq`)

The method cannot distinguish between them, so it errors instead of deleting only the unique_together constraint.

**Supporting evidence:**
- `_create_unique_sql` (line 1572): creates unique_together constraints with suffix `_uniq`
- `alter_index_together` (line 557): creates index_together with suffix `_idx`
- `_create_index_name` (lines 1259-1280): generates names as `{table}_{columns}_{hash}{suffix}`
- Test expects: delete `test_rutouf_pony_name_694f3b9f_uniq`, keep `test_rutouf_pony_name_key`

Confidence: **deduction — 98%**

The code path is clear, the naming conventions are documented, and the error message directly confirms the diagnosis.


## H₂: Edit sites and fix specification

**Primary edit site:**
`django/db/backends/base/schema.py` lines 559-580 (`_delete_composed_index` method)

**Current logic:**
1. Find all constraints matching columns and type
2. Expect exactly 1, error if != 1
3. Delete that constraint

**Required fix:**
1. Find all constraints matching columns and type
2. **When multiple found:** compute expected constraint name using `_create_index_name` with appropriate suffix
3. Filter constraints to find the one matching the expected Django-generated name
4. Delete that specific constraint (or handle case where expected name not found)

**Determining the suffix:**
- If `constraint_kwargs == {"unique": True}` → suffix is `"_uniq"` (unique_together)
- If `constraint_kwargs == {"index": True, "unique": False}` → suffix is `"_idx"` (index_together)

**Implementation approach:**
When `len(constraint_names) > 1`:
1. Compute `suffix` from `constraint_kwargs`
2. Call `expected_name = self._create_index_name(model._meta.db_table, columns, suffix)`
3. Filter `constraint_names` to find match: `[n for n in constraint_names if n == expected_name]`
4. If exactly 1 match found, delete it; otherwise handle appropriately

This preserves backward compatibility: when there's only 1 constraint (the common case), behavior is unchanged. When multiple exist (the bug case), it correctly identifies and deletes only the composed index.


## craft gate-loop iteration 1

**Fix applied:** Modified `_delete_composed_index` in `django/db/backends/base/schema.py` to filter multiple constraints by matching the expected Django-generated constraint name (with `_uniq` or `_idx` suffix) rather than raising ValueError immediately.

**Implementation:**
- When `len(constraint_names) != 1`, determine suffix based on `constraint_kwargs` (`_uniq` for unique_together, `_idx` for index_together)
- Generate expected constraint name using `_create_index_name()`
- Filter to matching constraint and delete only that one
- Preserves field-level unique constraints while removing composed constraints

**Gate result:** ✓ PASS
- All 132 tests passed (1 skipped)
- `test_remove_unique_together_on_unique_field` now passes
- No regressions detected

**Codex review:**
- Initial draft had indentation error (fixed)
- Logic validated as correct approach
- Concern raised about inferring suffix from constraint_kwargs (acceptable for current callers)

**Trajectory:** Convergent-success (green on first gate run after codex volley)


## Audit: django__django-15732

### FAIL_TO_PASS
- `test_remove_unique_together_on_unique_field (migrations.test_operations.OperationTests)`: **PASS** ✓

### PASS_TO_PASS regressions
None — all 132 tests passed (1 skipped)

### Pre-existing failures (not counted, confirmed against base capture)
None applicable — the FAIL_TO_PASS test was ERROR on base, now passes

### Gate output summary
```
Ran 132 tests in 1.033s
OK (skipped=1)
```

All tests in the suite passed, including the critical `test_remove_unique_together_on_unique_field` which was failing with `ValueError: Found wrong number (2) of constraints` on the base and now passes cleanly.

No regressions introduced. The fix correctly handles the case where a field has both `unique=True` and is part of `unique_together`, distinguishing between the field-level constraint and the composed constraint by matching Django's naming convention.

