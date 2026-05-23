# Django Issue #15563 - MTI Update Hypothesis Graph

## Initial Investigation
Model structure indicates multi-table inheritance with multiple parents.

---

# Hypothesis Graph: django__django-15563 (craft phase)

## Gate Iteration 1
**Attempt**: Added separate `related_update_ids` dict to store parent-specific IDs, selecting link fields for each parent using `link.attname`.
**Result**: Divergent - test_mti_update_parent_through_child PASSED, but test_mti_update_grand_parent_through_child still FAILED.
**Evidence**: Direct parent case (Congressman->Politician) works, but grandparent case (Senator->Politician) fails because `get_ancestor_link(Politician)` from Senator returns `congressman_ptr` (link to intermediate parent, not the target).

## Gate Iteration 2  
**Attempt**: Tried field lookup chaining approach with "__" syntax.
**Codex feedback (before gate)**: Caught critical bugs:
  - Duplicate PK selection (old + new both select PK, causing multi-column subquery error)
  - Row indexing would be off by 1
  - clone() doesn't preserve related_update_ids
**Fix applied**: Removed duplicate PK, added related_update_ids to clone()
**Result after fixes**: Regressive - BOTH tests now fail (was 1 pass, now 0 pass)
**Trajectory**: Divergent in wrong direction

## Gate Iteration 3
**Attempt**: V2 fix using field lookup paths like "congressman_ptr__politician_ptr_id"
**Result**: BOTH tests FAIL - same error pattern  
**Trajectory**: Oscillatory/stuck
**Root cause**: Django's `query.add_fields()` does NOT support "__" lookup syntax - that's only for filters. Cannot select from joined tables this way.

## Gate Iteration 4
**Attempt**: V3 fix - for grandparents, do follow-up ORM query to intermediate parent table to get target link IDs
**Result**: Text replacement failed - old code still present
**Check**: `grep -n "idents.extend" compiler.py` shows line 1867 still has old pattern
**Trajectory**: Stuck on implementation mechanics

## Assessment after 4 iterations (3 stuck)
**Diagnosis confidence**: HIGH - recon was correct about needing parent-specific link IDs
**Implementation blocker**: For grandparents (Senator->Politician), the needed field (politician_ptr_id) exists on intermediate table (Congressman), not on child table (Senator). Solutions attempted:
  1. "__" lookup syntax - doesn't work with add_fields()
  2. Follow-up query approach - text replacement failing in container

**Technical gap**: Need to either:
  - Use lower-level Django query API (setup_joins, add explicit join, reference joined alias column) 
  - OR ensure preselect query joins to parent tables and find correct API to select from joined table
  - OR accept multi-query approach and debug why text replacements aren't applying

The core Django question: How to SELECT a column from a JOINed parent table in the preselect query, when that parent is not a direct parent of the base model?

## H_recon_r4: Wrong parent link IDs used in MTI updates

**Mode**: Deduction (traced through code and verified with SQL logging)
**Confidence**: 95%

### Root Cause
When updating fields on parent models via MTI queryset updates, Django selects the child model's primary key and uses those IDs to filter ALL parent updates. This is incorrect because each parent has its own link field (e.g., `politician_ptr_id`), and the child's PK may be from a different parent (e.g., `person_ptr_id`).

### Evidence
Test case: `Congressman.objects.update(title="senator 1")` where:
- Congressman inherits from Person (PK: person_ptr_id) and Politician (link: politician_ptr_id)  
- Created Congressman has person_ptr_id=1, politician_ptr_id=2
- Current SQL: `UPDATE politician WHERE politician_id IN (1)` ← uses person_ptr_id
- Correct SQL: `UPDATE politician WHERE politician_id IN (2)` ← should use politician_ptr_id

From SQL logging:
```
Created Congressman: person_ptr_id=1, politician_ptr_id=2
SELECT congressman.person_ptr_id → [1]
UPDATE politician SET title='test' WHERE politician_id IN (1)  # WRONG!
```

### Code Path
1. `django/db/models/sql/compiler.py:1840` - `query.add_fields([query.get_meta().pk.name])` selects child PK
2. Line 1854-1857: Executes query, stores result in `self.query.related_ids`
3. `django/db/models/sql/subqueries.py:137` - All parent updates use the same `related_ids`: `query.add_filter("pk__in", self.related_ids)`

### Solution Approach
For each parent in `related_updates`, select the parent-specific link field IDs instead of the child's PK:
- **Direct parent** (Congressman→Politician): link field is on child table, select directly
- **Indirect parent** (Senator→Politician): link field is on intermediate table, need JOIN

Store parent-specific IDs in a dict mapping parent model → IDs, rather than a single `related_ids` list.

### Edit Sites
1. **django/db/models/sql/subqueries.py:63** - Change `self.related_ids = None` to `self.related_ids = {}`
2. **django/db/models/sql/compiler.py:1838-1857** - In `pre_sql_setup`, for each parent in `related_updates`, select the appropriate parent link field and store in `related_ids[parent_model]`
3. **django/db/models/sql/subqueries.py:136-137** - In `get_related_updates`, use `self.related_ids.get(model)` instead of `self.related_ids`

### Direct vs Indirect Parents
- **Direct**: Link field is on child's own table (e.g., Congressman has politician_ptr_id column)
  - Solution: SELECT the link field directly
- **Indirect**: Link field is on intermediate parent's table (e.g., Senator needs politician_ptr_id from Congressman table)
  - Solution: SELECT via JOIN through intermediate parent(s)
  - Use `model._meta.get_ancestor_link(parent)` to find the link field
  - For indirect links, join through the parent chain


## Craft Gate Loop - Iteration 1

**Approach**: Implemented recon's diagnosis with parent-specific link IDs using QuerySet.values_list() for relationship traversal.

**Changes**:
1. `django/db/models/sql/subqueries.py`:
   - Changed `related_ids` from `None` to `{}` (dict)
   - Updated `get_related_updates()` to use `related_ids.get(model)` for parent-specific IDs

2. `django/db/models/sql/compiler.py`:
   - Added `_get_parent_link_ids(child_ids, parent_model)` method to SQLUpdateCompiler
   - Builds field path from child to parent (e.g., "politician_ptr_id" for direct parent, "congressman_ptr__politician_ptr_id" for grandparent)
   - Uses QuerySet.values_list() to select parent link IDs with relationship traversal
   - Updated `pre_sql_setup()` to populate `related_ids[parent_model]` for each parent

**Key fix**: For direct parents, select the link field directly (e.g., `politician_ptr_id`). For indirect parents (grandparents), use Django's ORM relationship traversal (e.g., `congressman_ptr__politician_ptr_id`).

**Gate Result**: ✅ PASS
- test_mti_update_parent_through_child: ok
- test_mti_update_grand_parent_through_child: ok
- All 32 tests in model_inheritance_regress: OK (expected failures=1)
- No PASS_TO_PASS regressions

**Status**: RESOLVED
