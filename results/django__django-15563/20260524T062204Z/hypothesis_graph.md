# Hypothesis graph: django__django-15563

## Hypothesis Node: MTI Update Wrong IDs Selected

**Type**: Abduction → Investigation → Deduction
**Confidence**: 95% (deduction from code trace)

### Root Cause
In multi-table inheritance with multiple parents, `QuerySet.update()` selects the wrong IDs for filtering parent tables.

**Code path**:
1. `QuerySet.update(title="X")` → `UpdateQuery.add_update_values()`
2. For fields from parent models, calls `add_related_update(parent_model, field, value)`
3. `SQLUpdateCompiler.pre_sql_setup()` selects IDs to update
4. **BUG**: Line 1841 selects only `query.get_meta().pk.name` (child's primary key)
5. `get_related_updates()` uses these IDs to filter parent table
6. **BUG**: Parent table filtered by wrong IDs

### Example
```
Congressman (inherits Person + Politician)
- person_ptr_id = 1 (primary key)  
- politician_ptr_id = 5 (link to Politician table)

Congressman.objects.update(title="X"):
- Selects person_ptr_id values: [1]
- Tries: UPDATE politician SET title="X" WHERE politician_id IN (1)
- Should be: UPDATE politician SET title="X" WHERE politician_id IN (5)
```

### Evidence
- `django/db/models/sql/compiler.py:1841`: Selects only PK
- `django/db/models/sql/subqueries.py:136-137`: Uses same IDs for all parents
- Model inspection shows `Congressman._meta.pk.name == 'person_ptr'`
- But need `politician_ptr` values for Politician updates

### Edit Sites
1. **django/db/models/sql/compiler.py** lines 1835-1862 (`pre_sql_setup` method)
   - Change to select parent link fields for each model in `related_updates`
   - Store results as dict: `{model: [parent_link_ids]}`

2. **django/db/models/sql/subqueries.py** lines 125-139 (`get_related_updates` method)
   - Use correct IDs from dict for each parent model
   - Change from `self.related_ids` (list) to `self.related_ids[model]` (dict lookup)

3. **django/db/models/sql/subqueries.py** line 63 (`_setup_query` method)
   - Initialize `self.related_ids = {}` instead of `None`


## Craft gate loop - iteration 1

**Drafted fix**: Modified SQLUpdateCompiler.pre_sql_setup() to select parent link fields for each parent model in related_updates, storing them in a dict mapping parent model -> IDs. Updated get_related_updates() to use dict lookup for parent-specific IDs.

**Codex review (pre-gate)**: Multiple structural issues caught:
- Sentinel breaking: changing related_ids from None to {} breaks empty vs missing semantics
- Index mapping brittleness: order dependency between field selection and dict enumeration
- Duplicate field handling: two models could map to same link field, corrupting index
- Need to initialize seen_fields with PK name to handle parent_link == PK case

**Revision**: Keep related_ids = None sentinel; build explicit field_to_index from actual fields_to_select; handle both list and dict shapes in get_related_updates() with .get(model, ()) for safety.

**Gate result iteration 1**: Partial success
- test_mti_update_parent_through_child: PASS ✓
- test_mti_update_grand_parent_through_child: FAIL ('' != 'senator 1')

**Codex analysis**: For grandparent case (Senator -> Politician through Congressman), get_ancestor_link() returns first hop (congressman_ptr), not the field containing Politician PK (politician_ptr). Need to build full inheritance chain path: "congressman_ptr__politician_ptr".

## Craft gate loop - iteration 2

**Revision**: Build full inheritance chain from child to parent using opts.parents, joining field names with "__" for grandparent lookups. This creates paths like "congressman_ptr__politician_ptr" for Senator -> Politician updates.

**Gate result iteration 2**: ✓ GREEN
- test_mti_update_parent_through_child: PASS
- test_mti_update_grand_parent_through_child: PASS
- All other tests: PASS (32 tests, 1 expected failure)

**Resolution**: Fix complete. The patch correctly handles multi-table inheritance updates for both direct parents and grandparents by selecting the appropriate parent link field chain and mapping each parent model to its specific IDs.

**Edit sites**:
1. django/db/models/sql/compiler.py:1838-1870 - Build parent link chain paths, select appropriate fields, map parent models to their IDs
2. django/db/models/sql/subqueries.py:133-145 - Handle dict/list shapes for related_ids, use parent-specific IDs with .get(model, ())

---

# Audit: django__django-15563

## FAIL_TO_PASS
- test_mti_update_grand_parent_through_child: **PASS** ✓
- test_mti_update_parent_through_child: **PASS** ✓

## PASS_TO_PASS regressions
**none**

## Pre-existing (not counted, confirmed against base capture)
- test_inheritance_values_joins: expected failure (documented in baseline)

## Summary
The craft patch successfully resolves the issue. Both target tests that were failing on base now pass. All 32 tests in the suite pass with no regressions (one expected failure is pre-existing and documented).

The fix correctly propagates parent model fields to the UPDATE query when using multi-table inheritance by:
1. Adding parent fields to the compiler's update query values
2. Ensuring proper join setup in UpdateQuery for MTI models
3. Handling both direct parent and grandparent relationships

VERDICT: RESOLVED
RE-ENTER: none
