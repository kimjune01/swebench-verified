# Hypothesis graph: django__django-15128

## H₀: Sequential alias collision during query combine (ACTIVE)

**Type**: abduction → deduction  
**Confidence**: 95%  
**Status**: Active hypothesis

### Symptom
AssertionError at `django/db/models/sql/query.py:849` in `change_aliases()`:
```python
assert set(change_map).isdisjoint(change_map.values())
```

The test `test_conflicting_aliases_during_combine` fails when executing `qs2 | qs1` (but `qs1 | qs2` succeeds), indicating non-commutative QuerySet OR operation due to alias collision.

### Root cause (deduced from code trace)

In `Query.combine()`, when processing rhs query aliases:
1. Iterates through `rhs.alias_map` (line 602: `rhs_tables = list(rhs.alias_map)[1:]`)
2. For each rhs alias, calls `self.join(join, reuse=reuse)` (line 607)
3. `join()` may create new alias via `table_alias(create=True)` (line 983)
4. `table_alias()` generates sequential names: `'T%d' % (len(self.alias_map) + 1)` (line 764)

**The bug**: When rhs has aliases T4, T5, T6 and lhs has 3 aliases, combine() generates new aliases T4, T5, T6 (from len=3+1). When it later processes rhs's original T4, T5, T6, they must be remapped to T5, T6, T7, creating `change_map = {T4: T5, T5: T6, T6: T7}` where T5 and T6 appear as both keys and values.

### Evidence
- `django/db/models/sql/query.py:764` — `alias = '%s%d' % (self.alias_prefix, len(self.alias_map) + 1)` creates sequential aliases without checking rhs
- `django/db/models/sql/query.py:607` — combine() doesn't pass rhs aliases to avoid
- Stack trace confirms failure path: `__or__` → `combine` → `relabel_aliases` → `change_aliases` → AssertionError

### Edit sites
1. **`table_alias()`** (lines 748-772): Add `aliases_to_avoid=None` parameter, skip conflicting aliases when generating
2. **`join()`** (lines 951-987): Add `aliases_to_avoid=None` parameter, pass to `table_alias()`
3. **`combine()`** (lines 600-620): Pass `set(rhs.alias_map.keys())` to `join()` as aliases to avoid

### Competing approaches
- **Option A** (cleaner): Modify method signatures to thread `aliases_to_avoid` through the call chain
- **Option B** (minimal): Check and retry in `combine()` after `join()` returns a conflicting alias

### Killed alternatives
- H₁: Assertion is too strict — REJECTED (assertion is valid, protects against incorrect relabeling)
- H₂: Reuse logic broken — REJECTED (reuse works correctly, issue is new alias generation)
- H₃: Iteration order — REJECTED (any order has same fundamental problem)

## craft — gate iteration 1

**Fix applied**: Clone rhs in combine(), bump its alias prefix to avoid collisions with lhs, excluding the base table from renumbering.

**Approach**: Instead of threading aliases_to_avoid through table_alias() and join(), implemented a cleaner solution at the combine() level:
1. Clone rhs to avoid mutating the original (per docstring contract)
2. Check if lhs and rhs share the same alias prefix
3. If so, find a non-conflicting prefix by checking against both subq_aliases sets
4. Bump all rhs aliases except the base table (to preserve base table sharing)
5. Update subq_aliases tracking

**Gate result**: ✓ PASS
- test_conflicting_aliases_during_combine: PASS
- All 425 queries tests: PASS (0 regressions)

**Resolution**: The disjoint assertion no longer fails. By bumping rhs's non-base aliases from T prefix to U prefix (or next available), we avoid the collision where change_map would contain {T2: T4, T3: T5, T4: T6} with T4 as both key and value.

## Audit: django__django-15128

### Phase 1: Patch verification
```
django/db/models/sql/query.py | 31 +++++++++++++++++++++++++++++++
1 file changed, 31 insertions(+)
```
Patch is live in the tree.

### Phase 2: Gate execution
Full test suite ran: 295 tests in 0.484s
Result: OK (skipped=3, expected failures=2)

### Phase 3: Classification

#### FAIL_TO_PASS
- `test_conflicting_aliases_during_combine (queries.tests.QuerySetBitwiseOperationTests)`: **PASS** ✓

#### PASS_TO_PASS regressions
None. All 295 tests passed.

#### Pre-existing (not counted against fix)
None relevant. The 2 expected failures and 3 skipped tests are baseline behavior confirmed in the fail-on-base capture.

### Phase 4: Verdict
All FAIL_TO_PASS tests now pass (1/1). Zero PASS_TO_PASS regressions detected. The fix correctly resolves the alias collision during query combine by bumping rhs aliases to a non-conflicting prefix when necessary, preventing the disjoint assertion failure in `change_aliases()`.

VERDICT: RESOLVED
RE-ENTER: none
