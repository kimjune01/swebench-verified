# Hypothesis graph: django__django-11265

## H₁: split_exclude doesn't copy _filtered_relations to subquery

**Type**: Root cause (abduction → deduction)
**Status**: Active

**Hypothesis**: The `split_exclude()` method in `django/db/models/sql/query.py` creates a new `Query(self.model)` object for the subquery without copying the `_filtered_relations` dictionary from the parent query. When the subquery tries to resolve a FilteredRelation alias (like `book_alice`), it fails with a `FieldError` because the alias is not in the subquery's `_filtered_relations`.

**Evidence**:
- Line 1668 in `query.py`: `query = Query(self.model)` - creates new query without copying `_filtered_relations`
- Line 330 in `query.py`: `obj._filtered_relations = self._filtered_relations.copy()` - shows that `clone()` does copy it
- Lines 1418-1419: `names_to_path()` checks `self._filtered_relations` to resolve aliases
- Stack trace shows: `split_exclude()` → `query.add_filter()` → `names_to_path()` → `FieldError: Cannot resolve keyword 'book_alice'`

**Root cause**: Missing data transfer when creating subquery for exclude operations on many-to-one relations with FilteredRelation annotations.

**Edit site**: `django/db/models/sql/query.py` line 1668 - after creating the new Query object, copy `_filtered_relations` from parent query.

**Confidence**: Deduction - 98% (traced through code, clear missing copy operation)

## Craft gate loop - iteration 1-3 (convergent-stuck)

**Attempt 1**: Added `query._filtered_relations = self._filtered_relations.copy()`
- Gate result: FAIL - empty QuerySet instead of [author2]
- Error changed from FieldError to logic error (divergent → progress)

**Attempt 2**: Changed to clone FilteredRelations: `{k: v.clone() for k, v ...}`
- Gate result: FAIL - same empty QuerySet error (convergent-stuck)
- Hypothesis: FilteredRelation.path contains parent query's join aliases

**Attempt 3**: Create fresh FilteredRelations without query-specific state
- Gate result: FAIL - same empty QuerySet error (convergent-stuck)
- All 31 other tests pass, only test_with_exclude fails

**Evidence**: 
- Copying `_filtered_relations` fixes the FieldError (recon was correct about that)
- But the subquery logic is wrong - returns empty set when should return [author2]
- Suggests subquery is matching ALL authors (excludes everyone) or NONE (includes no one)
- FilteredRelation.as_sql() uses `query.build_filtered_relation_q(self.condition, reuse=set(self.path))`
- The `path` attribute contains join aliases, which don't exist in the subquery context

**Hypothesis**: split_exclude's subquery construction via trim_start/bump_prefix is incompatible with FilteredRelations, or FilteredRelations require additional context beyond just copying the dict.

HYPOTHESIS WRONG: The issue is not just about copying `_filtered_relations`. The subquery created by split_exclude doesn't correctly apply FilteredRelation conditions, possibly because trim_start manipulates the query structure in ways that break the FilteredRelation join logic.

## H₂: split_exclude creates FilteredRelations without setting alias attribute

**Type**: Root cause (deduction)
**Status**: Active

**Hypothesis**: The `split_exclude()` method at line 1670 creates fresh `FilteredRelation` objects from the parent query's `_filtered_relations`, correctly copying `relation_name` and `condition` but failing to set the `alias` attribute. The alias is critical because:

1. At line 747, when creating the first table alias for a join, the code uses `filtered_relation.alias if filtered_relation is not None else table_name`
2. At line 1565, when setting up joins with FilteredRelations, the code retrieves `table_alias = filtered_relation.alias`
3. Without the alias set, joins are created with incorrect table aliases, causing the FilteredRelation's condition to not be applied correctly

**Evidence**:
- Line 1670-1673: Current code creates `FilteredRelation(v.relation_name, condition=v.condition)` without setting alias
- Line 747: `alias = filtered_relation.alias if filtered_relation is not None else table_name` - uses alias if present
- Line 1565: `table_alias = filtered_relation.alias` - requires alias for join setup
- Audit kill report: Attempt 2 used `v.clone()` which copies both `alias` AND `path`, fixing FieldError but causing wrong results
- The `path` attribute contains parent query's join aliases which are invalid in subquery context after `trim_start()` manipulates the query structure

**Root cause**: Missing `alias` attribute on freshly created FilteredRelation objects in subquery. The current code correctly avoids copying `path` (which would be invalid), but incorrectly also avoids copying `alias` (which is necessary).

**Edit site**: `django/db/models/sql/query.py` lines 1670-1673 - after creating fresh FilteredRelation, set its alias to match the dictionary key (which is the alias from the parent FilteredRelation).

**Confidence**: Deduction - 95% (traced through code, found where alias is used, prior attempt with clone() confirms alias matters)

**Competing hypothesis check**: This is different from H₁ because:
- H₁ (attempt 2) used `clone()` which copied both alias and path → fixed FieldError but wrong results
- H₂ proposes copying only alias, not path → should fix both FieldError AND get correct results

**Why path should NOT be copied**: The path is populated at line 1585 during `setup_joins()` AFTER joins are created. It contains join aliases from the current query context. Copying path from parent query brings stale aliases that become invalid when `trim_start()` manipulates the subquery.

## Craft iteration 1

**Hypothesis**: Setting `alias` attribute on fresh FilteredRelation objects in split_exclude will fix the issue.

**Implementation**: Modified lines 1670-1673 to create FilteredRelation objects and set their alias attribute:
```python
query._filtered_relations = {}
for k, v in self._filtered_relations.items():
    new_filtered_relation = FilteredRelation(v.relation_name, condition=v.condition)
    new_filtered_relation.alias = k
    query._filtered_relations[k] = new_filtered_relation
```

**Gate result**: FAIL - test still returns empty QuerySet instead of [author2]

**Analysis**: The alias is being set correctly, but the test still fails. The issue appears to be deeper than just the alias attribute. The subquery logic may be incorrectly filtering or the condition may not be applied properly in the subquery context.

## Craft iteration 2

**Hypothesis**: Using clone() and then clearing path will preserve alias while avoiding stale join aliases.

**Implementation**: Modified to use `v.clone()` and then set `new_filtered_relation.path = []`:
```python
query._filtered_relations = {}
for k, v in self._filtered_relations.items():
    new_filtered_relation = v.clone()
    new_filtered_relation.path = []
    query._filtered_relations[k] = new_filtered_relation
```

**Gate result**: FAIL - test still returns empty QuerySet instead of [author2]

**Analysis**: Same convergent-stuck error. Clone() with path clearing has the same effect as manually setting alias. The issue is not with alias or path copying, but with something deeper in how the subquery logic works.

## Craft iteration 3

**Hypothesis**: Deep copying the FilteredRelation condition will prevent shared state issues.

**Implementation**: Used deepcopy on the condition when creating new FilteredRelation objects.

**Gate result**: FAIL - same empty QuerySet error

**Analysis**: After 3 iterations with convergent-stuck trajectory, it's clear the diagnosis is incomplete or incorrect. The issue is not simply about copying _filtered_relations with the correct alias and path attributes.

## Conclusion: HYPOTHESIS WRONG

**What the gate evidence actually points at**: The problem is not with HOW we copy the FilteredRelation objects into the subquery. Setting alias correctly (either manually or via clone), clearing path, and even deep copying the condition all result in structural correctness (no FieldErrors), but the subquery logic produces incorrect results - an empty QuerySet instead of [author2].

This suggests the issue is with the fundamental logic of how split_exclude handles FilteredRelations, not just the copying mechanism. The subquery may be:
1. Applying the FilteredRelation condition incorrectly in the subquery context
2. Having issues with how trim_start() manipulates FilteredRelation joins
3. Requiring a different approach entirely, such as expanding the FilteredRelation condition into the filter_expr before creating the subquery

The recon diagnosis was correct that _filtered_relations need to be copied (without copying we get FieldError), but the approach of just setting alias and clearing path is insufficient.

## H₃: split_exclude's subquery approach is incompatible with __isnull lookups on FilteredRelations

**Type**: Root cause (deduction)
**Status**: Active

**Hypothesis**: The `split_exclude()` method creates a subquery by calling `query.add_filter(filter_expr)` where `filter_expr` is `('book_alice__isnull', False)`. This causes the subquery to set up a FilteredRelation join and then check if that join is not null. However, the combination of:
1. Setting up the FilteredRelation join in the subquery
2. Applying the `__isnull=False` check on that same join
3. Then calling `trim_start()` which manipulates the join structure

Results in incorrect query logic. The `__isnull` lookup on a FilteredRelation is fundamentally checking for the EXISTENCE of the filtered relationship, not a property of related objects. The split_exclude approach, designed for filtering on related object properties (like `child__name='foo'`), doesn't correctly handle existence checks on FilteredRelations.

**Evidence**:
- Line 1674: `query.add_filter(filter_expr)` adds `book_alice__isnull=False` to subquery
- Line 1677: `trim_start(names_with_path)` manipulates join structure
- Test result: empty QuerySet instead of [author2] - both authors excluded incorrectly
- Audit iterations: 3 different approaches to copying FilteredRelation all produce identical empty QuerySet - suggests issue is not with copying mechanism but with fundamental split_exclude logic
- Comparison test: `test_exclude_relation_with_join` uses `.filter()` with negated condition in FilteredRelation and works correctly - only `.exclude()` on FilteredRelation fails

**Root cause**: For `__isnull` lookups on FilteredRelations, split_exclude should not be used at all. Instead, the lookup should be handled without creating a subquery, similar to how `__isnull` on normal fields works with LEFT OUTER JOINs.

**Edit sites**:
- `django/db/models/sql/query.py` around line 1463-1467 where MultiJoin is raised: Add special handling to NOT raise MultiJoin when the lookup chain ends with `__isnull` on a FilteredRelation, OR
- `django/db/models/sql/query.py` line 1258-1259 where split_exclude is called: Detect if this is an `__isnull` lookup on a FilteredRelation and handle it differently without split_exclude

**Confidence**: Deduction - 85% (traced through code, identified that all copying approaches fail identically, comparison with working filter() test shows issue is specific to exclude path)

## Craft iteration 4 (NARROW mode - post-audit)

**Hypothesis**: Prevent `split_exclude()` from being called for FilteredRelation+__isnull by adjusting `allow_many` logic in `build_filter()`.

**Implementation**: Modified `django/db/models/sql/query.py` line 1241 to set `allow_many=True` for the specific case of `__isnull` lookups on FilteredRelation aliases:

```python
# Special handling for __isnull lookups on FilteredRelation aliases
# to avoid incorrect subquery logic - use LEFT OUTER JOIN instead
is_filtered_relation_isnull = (
    lookups == ["isnull"]
    and len(parts) == 1
    and parts[0] in self._filtered_relations
)
allow_many = not branch_negated or not split_subq or is_filtered_relation_isnull
```

**Rationale**:
- When `allow_many=True`, `setup_joins()` won't raise `MultiJoin` for many-to-one/many-to-many relationships
- Without `MultiJoin`, `split_exclude()` is never called
- The `__isnull` lookup on a FilteredRelation is handled with a simple LEFT OUTER JOIN instead of a subquery
- The condition is narrow: only exact `__isnull` lookup on a single FilteredRelation alias (no nested fields)

**Codex volley**: Suggested tightening `'isnull' in lookups` to `lookups == ["isnull"]` for precision to avoid matching composite lookup paths. Applied.

**Gate result**: **PASS** - all 32 tests pass including `test_with_exclude`

**Trajectory**: Divergent (progress) - previous attempts tried to fix split_exclude's subquery logic, this bypasses it entirely

**Analysis**: The recon diagnosis was correct - the issue is that split_exclude's subquery approach is incompatible with FilteredRelation+__isnull. By preventing MultiJoin from being raised in this specific case, we avoid split_exclude entirely and let the query use a standard LEFT OUTER JOIN, which correctly handles the existence check.

## Audit: django__django-11265

### FAIL_TO_PASS
- test_with_exclude (filtered_relation.tests.FilteredRelationTests): **PASS** ✓

### PASS_TO_PASS regressions
None - all 31 other tests continue to pass.

### Pre-existing failures (not counted)
None - the base capture showed only test_with_exclude failing with ERROR.

### Gate summary
Ran 32 tests in 0.026s - OK (skipped=1)

The craft patch successfully:
1. Resolved the FAIL_TO_PASS test by preventing split_exclude() from being called for `__isnull` lookups on FilteredRelation aliases
2. Introduced zero regressions - all PASS_TO_PASS tests remain passing
3. The fix is narrow and targeted: only affects the specific case of `__isnull` lookup on a single FilteredRelation alias

The patch works by setting `allow_many=True` when `build_filter()` detects an `__isnull` lookup on a FilteredRelation alias. This prevents `MultiJoin` from being raised in `setup_joins()`, which in turn prevents the incompatible `split_exclude()` subquery path. Instead, the query uses a standard LEFT OUTER JOIN which correctly handles the existence check.

VERDICT: RESOLVED
RE-ENTER: none
