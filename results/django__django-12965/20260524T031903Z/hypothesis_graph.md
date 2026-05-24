# Hypothesis graph: django__django-12965

## H1: single_alias check returns False for empty alias_map (abduction, 90%)

**Observation**: Test `test_fast_delete_all` fails because `User.objects.all().delete()` generates SQL with a subquery: `DELETE FROM "delete_user" WHERE "delete_user"."id" IN (SELECT "delete_user"."id" FROM "delete_user")` instead of the expected simple `DELETE FROM "delete_user"`.

**Root cause**: In commit 7acef095d7, Django moved DELETE SQL generation from `DeleteQuery.delete_qs()` to `SQLDeleteCompiler.as_sql()`. The new implementation checks a `single_alias` property to decide between simple DELETE vs subquery:

```python
@cached_property
def single_alias(self):
    return sum(self.query.alias_refcount[t] > 0 for t in self.query.alias_map) == 1
```

For `User.objects.all().delete()`:
- When `_raw_delete()` clones the query and converts it to DeleteQuery, `alias_map` is empty `{}`
- `alias_refcount` is also empty `{}`  
- `sum(...)` over empty iteration = 0
- `0 == 1` returns False
- Code falls back to subquery path unnecessarily

**Evidence**:
- `django/db/models/sql/compiler.py:1408-1409` - single_alias property
- `django/db/models/sql/compiler.py:1423-1436` - as_sql() branches on single_alias
- Git diff `7acef095d7` shows old `delete_qs()` called `get_initial_alias()` before checking table count, new code doesn't

**Fix**: Change line 1409 from `== 1` to `<= 1` to handle the empty alias_map case (0 tables with refcount > 0 means simple base-table query).

**Supporting code**:
```python
# OLD code (removed in 7acef095d7):
innerq.get_initial_alias()  # Ensured base table was in alias_map
self.get_initial_alias()
innerq_used_tables = tuple([t for t in innerq.alias_map if innerq.alias_refcount[t]])
if not innerq_used_tables or innerq_used_tables == tuple(self.alias_map):  # 0 or 1 tables
    self.where = innerq.where  # Simple delete
```

Confidence: **abduction - 90%** (deduced from code inspection and git history, not experimentally verified within container)


## Craft iteration 1

**Hypothesis**: The `single_alias` property in `SQLDeleteCompiler` incorrectly rejects empty alias_map queries (returns False when `sum({}) == 1`), causing simple `DELETE FROM table` to use the subquery path.

**Intervention**: 
1. Added explicit `self.query.get_initial_alias()` call to populate alias_map before checking
2. Changed comparison from `== 1` to `<= 1` to handle both:
   - 0 aliases (empty alias_map after initial setup for base-table-only queries)
   - 1 alias (single-table queries with joins)

**File**: `django/db/models/sql/compiler.py` lines 1410-1411

**Gate result**: ✓ PASS (all 54 tests, including `test_fast_delete_all`)

**Evidence trajectory**: Convergent-resolved — the failing test now passes, all existing tests remain green.


## Audit: django__django-12965

### Patch verification
- Patch is live: `django/db/models/sql/compiler.py` modified (2 insertions, 1 deletion)
- Gate ran: 54 tests in 0.789s

### FAIL_TO_PASS
- `test_fast_delete_all (delete.tests.FastDeleteTests)`: **PASS** ✓

### PASS_TO_PASS
All specified PASS_TO_PASS tests verified as passing:
- test_fast_delete_combined_relationships: PASS ✓
- test_fast_delete_empty_no_update_can_self_select: PASS ✓
- test_fast_delete_fk: PASS ✓
- test_fast_delete_inheritance: PASS ✓
- test_fast_delete_instance_set_pk_none: PASS ✓
- test_fast_delete_joined_qs: PASS ✓
- test_fast_delete_large_batch: PASS ✓
- test_fast_delete_m2m: PASS ✓
- test_fast_delete_qs: PASS ✓
- test_fast_delete_revm2m: PASS ✓
- test_auto: PASS ✓
- test_auto_nullable: PASS ✓
- test_cascade: PASS ✓
- test_cascade_from_child: PASS ✓

### Regressions
**None** — all 54 tests in suite passed, zero PASS_TO_PASS regressions

### Pre-existing failures
**None** — baseline showed `test_fast_delete_all` failing before patch, now fixed

### Classification
- All FAIL_TO_PASS tests now pass ✓
- Zero PASS_TO_PASS regressions ✓
- Fix is minimal and targeted (3-line change)

The patch correctly identifies the root cause: the `single_alias` property returned False for queries with empty alias_map (sum of 0 aliases ≠ 1). The fix adds `get_initial_alias()` to ensure alias_map is populated, then changes comparison to `<= 1` to handle both 0-alias (base table only) and 1-alias (simple join) cases.

VERDICT: RESOLVED
RE-ENTER: none
