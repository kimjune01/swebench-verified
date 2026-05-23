# Hypothesis graph: django__django-16263

## H₀: Initial Diagnosis (abduction)

**Date:** 2026-05-23
**Mode:** abduction
**Confidence:** 75%

The tests fail because `get_aggregation()` doesn't prune unreferenced annotations from count queries.

**Failure symptoms:**
1. `test_unused_aliased_aggregate_pruned` - expects 1 SELECT, gets 2 (unnecessary subquery)
2. `test_non_aggregate_annotation_pruned` - expects 1 SELECT, gets 2 (unnecessary subquery)
3. `test_unreferenced_aggregate_annotation_pruned` - expects "authors_count" not in SQL, but it appears

**Root cause:**
In `django/db/models/sql/query.py::get_aggregation()` (lines 444-463), the `existing_annotations` list includes ALL annotations regardless of whether they're referenced in the query. This forces:
- Unnecessary subqueries (line 456: `or existing_annotations`)
- Unused annotations in the SELECT clause (line 474: `set_annotation_mask(self.annotation_select)`)

**Supporting evidence:**
- `django/db/models/sql/query.py:451-454` - Comment says "we aren't smart enough to remove the existing annotations from the query"
- `django/db/models/sql/query.py:444-448` - `existing_annotations` built from all annotations without checking references
- `django/db/models/sql/query.py:456` - Condition `or existing_annotations` is always True when annotations exist

**Expected behavior:**
- Non-aggregate unreferenced annotations: should not force subquery, should be pruned completely
- Aggregate unreferenced annotations: still need subquery (for GROUP BY) but should not appear in SELECT


## Edit Sites Detail

**File: `django/db/models/sql/query.py`**

1. **New helper method** (insert before line 438):
   - Method to collect referenced annotation aliases
   - Walk `self.where`, `self.order_by`, and annotation values
   - Return set of annotation aliases that are referenced

2. **Lines 444-463 - existing_annotations logic**:
   - After line 448, call the helper to get referenced aliases
   - Filter list to exclude unreferenced non-aggregate annotations
   - Keep unreferenced aggregate annotations (for GROUP BY) but track them separately

3. **Line 474 - annotation mask**:
   - Create filtered mask excluding unreferenced annotations
   - Use: `inner_query.set_annotation_mask(filtered_mask)` instead of `self.annotation_select`

## Code Pattern to Find References

Expression objects with references to annotations:
- `F(name)` - has `.name` attribute pointing to field/annotation
- `Ref(alias, source)` - has `.refs` attribute pointing to annotation alias
- Need to recursively walk via `get_source_expressions()` method on Expression objects


## Gate Loop - Iteration 1

**Status**: Stuck - multiple approaches tried, some FAIL_TO_PASS tests pass but new regressions introduced

**Changes made**:
1. Added `_get_referenced_annotations()` helper method to find annotations referenced in WHERE, ORDER BY, added aggregates, and other annotations
2. Modified `get_aggregation()` to use `annotation_select` instead of `annotations` for subquery decision (distinguishes `.alias()` from `.annotate()`)
3. Added F-expression detection in addition to Ref detection
4. Imported F class

**Current state**:
- `test_unused_aliased_aggregate_pruned`: PASSING (2/3)
- `test_unreferenced_aggregate_annotation_pruned`: PASSING (2/3)
- `test_non_aggregate_annotation_pruned`: FAILING - "name_lower" appears in SQL when it shouldn't (no subquery correctly avoided, but annotation not pruned)
- NEW REGRESSIONS: `test_aggregation_default_after_annotation` and `test_annotate_values_aggregate` fail with result=0 instead of expected values

**Root cause of regressions**: Annotations referenced by added aggregates (e.g., `Sum("field_name")`) are not being detected as referenced, so they're being pruned from the mask, causing aggregate calculations to fail.

**Hypothesis**: F-expression detection is not working correctly, OR the timing of when aggregates are resolved means F expressions haven't been created yet when we check references.

**Next steps needed**:
1. Debug why F-expression references aren't being detected
2. Handle the no-subquery case where annotations need to be pruned from the SELECT
3. Consider alternative approaches if current method is fundamentally flawed

## Gate Loop - Final Assessment (Iteration 3)

**HYPOTHESIS WRONG**: The recon diagnosis correctly identified that `get_aggregation()` doesn't prune unreferenced annotations, but the proposed fix approach of detecting references via Ref/F expression traversal is insufficient.

**What the gate evidence actually points at**:
1. F-expression detection is not capturing references from added aggregates (e.g., `Sum("field_name")`) to existing annotations, despite correctly importing F and checking `isinstance(expr, F)`
2. Setting annotation mask to empty set or referenced-only causes SQL syntax errors ("near FROM") in many cases
3. The timing of when aggregates are resolved vs. when we check references may be incompatible with this approach
4. Need to handle both subquery and no-subquery paths differently for pruning

**Attempted fixes (all failed)**:
- Added `_get_referenced_annotations()` helper with Ref and F checks
- Modified subquery decision to use `annotation_select` vs `annotations` 
- Attempted pruning in both subquery and no-subquery paths
- All attempts either fail to detect references or cause SQL generation errors

**Current gate status**: 2/3 FAIL_TO_PASS tests pass but with 3 failures + 12 errors total
- `test_unused_aliased_aggregate_pruned`: PASS
- `test_unreferenced_aggregate_annotation_pruned`: PASS  
- `test_non_aggregate_annotation_pruned`: FAIL (annotation not pruned in no-subquery case)
- NEW REGRESSIONS: `test_aggregation_default_after_annotation`, `test_annotate_values_aggregate` (results=0 due to over-pruning)

**Conclusion**: Current approach cannot reliably detect which annotations are referenced. Need to re-diagnose to find a different mechanism or leverage existing Django annotation dependency tracking.

## Hypothesis H1: Non-subquery path doesn't prune unreferenced annotations

**Type**: abduction  
**Confidence**: 85%

### Observation
The test `test_non_aggregate_annotation_pruned` shows that when calling `.annotate(name_lower=Lower("name")).count()`, the SQL includes `name_lower` in the SELECT clause even though it's not referenced:
```sql
SELECT LOWER("aggregation_book"."name") AS "name_lower", COUNT(*) AS "__count" FROM "aggregation_book"
```

Expected: only `COUNT(*) AS "__count"` should be selected.

### Root Cause
In `django/db/models/sql/query.py::get_aggregation()` (lines 483-610):

1. The method computes `referenced_annotations` (line 500-502) - the set of existing annotations that are actually referenced
2. In the **subquery path** (lines 521-596), it correctly prunes unreferenced annotations:
   ```python
   if referenced_annotations:
       inner_query.set_annotation_mask(referenced_annotations)
   else:
       inner_query.set_annotation_mask(set())
   ```
3. In the **non-subquery path** (lines 597-600), it does NOT prune:
   ```python
   else:
       outer_query = self
       self.select = ()
       self.default_cols = False
       self.extra = {}
       # Missing: set_annotation_mask call!
   ```

The non-subquery path is taken when there are no existing aggregate annotations (`existing_annotations` is empty), which happens for:
- Non-aggregate annotations like `Lower("name")`  
- Aliased annotations (`.alias()` doesn't add to `annotation_select`)

### Evidence
- `django/db/models/sql/query.py` line 597-600: non-subquery else branch has no mask setting
- `django/db/models/sql/query.py` line 548-551: subquery path sets the mask correctly
- `django/db/models/sql/query.py` line 504-508: existing_annotations only includes annotations with `contains_aggregate`

### Required Fix
In the non-subquery path (after line 599), add:
```python
self.set_annotation_mask(referenced_annotations | set(added_aggregate_names))
```

This will:
- Keep only referenced existing annotations
- Keep the newly added aggregates (like `__count`)
- Prune all unreferenced annotations


## Craft iteration 2 - STUCK

### Approach
Added annotation pruning logic to both find referenced annotations and set the annotation mask in the non-subquery path.

Changes:
1. Added `existing_annotation_names` computation
2. Added reference-finding loop that checks F/Ref expressions
3. Modified `existing_annotations` filter to only include aggregates (`contains_aggregate=True`)
4. Added `set_annotation_mask()` call in non-subquery path

### Gate result
- test_non_aggregate_annotation_pruned: PASS ✓
- test_unused_aliased_aggregate_pruned: FAIL (using subquery when shouldn't)
- test_unreferenced_aggregate_annotation_pruned: FAIL (annotation in subquery SELECT)
- PASS_TO_PASS regressions: test_aggregation_default_after_annotation (0!=40), test_annotate_values_aggregate (0!=337)

### Debug findings
- Mask is set correctly: `{'double_num_awards', 'value'}`
- annotation_select contains correct keys after mask
- But aggregate result is 0 instead of expected value

### Hypothesis
The issue is likely that:
1. Test #2 and #3 failures suggest we also need to handle the subquery path and `.alias()` cases
2. The PASS_TO_PASS regressions (result=0) suggest the annotation values aren't being computed even though they're in the mask
3. The fix needs to be NARROWER - only prune when it's a `.count()` operation, not general `.aggregate()`

The recon diagnosis may be incomplete - it only addressed the non-subquery path, but tests #2 and #3 require additional handling.


## Craft iteration 3 - CONVERGENT STUCK (3 iterations, hypothesis appears wrong)

### Final approach tried
1. Added reference-finding logic (checks F/Ref expressions)
2. ONLY set annotation mask in non-subquery path for count() operations (`if added_aggregate_names == ["__count"]`)
3. Did NOT modify existing_annotations filter

### Gate result (unchanged from iteration 2)
- test_non_aggregate_annotation_pruned: PASS ✓ (1/3 FAIL_TO_PASS)
- test_unused_aliased_aggregate_pruned: FAIL (subquery when shouldn't)
- test_unreferenced_aggregate_annotation_pruned: FAIL (not pruning in subquery)
- PASS_TO_PASS regressions persist: test_aggregation_default_after_annotation (0!=40), test_annotate_values_aggregate (0!=337)

### Why hypothesis is wrong
1. The recon diagnosis only addressed the non-subquery path, but tests #2 and #3 require handling of `.alias()` and subquery paths
2. PASS_TO_PASS regressions occur even with narrowing to count() only, suggesting the reference-finding logic or `existing_annotation_names` computation is interfering
3. After 3 stuck iterations with same error, the root cause is likely different from what recon identified

The non-subquery annotation mask approach works for test #1 but breaks other cases. Need fresh diagnosis covering:
- How `.alias()` annotations interact with aggregation
- Why subquery path doesn't prune (test #3)
- Why PASS_TO_PASS tests get 0 results even when annotations are in the mask

## H2: Incomplete diagnosis - missing `.alias()` handling and subquery pruning

**Type**: deduction
**Confidence**: 90%

### Root Cause Analysis

The previous diagnosis correctly identified the non-subquery path needs pruning (test #1), but missed two critical issues:

1. **`.alias()` annotations trigger unnecessary subqueries** (test #2)
   - Line 469 uses `self.annotations.items()` which includes BOTH `.annotate()` and `.alias()` annotations
   - `.alias()` sets `select=False`, so these annotations are NOT in `annotation_select`
   - But they ARE in `annotations`, so they trigger the subquery condition
   - Fix: Change to `self.annotation_select.items()` to exclude alias annotations

2. **Subquery path doesn't prune unreferenced annotations** (test #3)  
   - Line 508 sets `inner_query.set_annotation_mask(self.annotation_select)` 
   - This includes ALL selected annotations, not just referenced ones
   - Unreferenced aggregate annotations appear in the inner query SELECT when they shouldn't
   - Fix: Change to `inner_query.set_annotation_mask(referenced_annotations)`

### Why PASS_TO_PASS tests fail with current code

The addition of `contains_aggregate` filter on line 469 changes which queries take the subquery path:
- Non-aggregate annotations (like `F("field") * 2`) no longer trigger subqueries
- But `.values()` calls still NEED subqueries due to GROUP BY
- Fortunately, `.values()` sets `group_by` to a tuple via `set_group_by()` (query.py:1664)
- So `isinstance(self.group_by, tuple)` on line 473 triggers the subquery path anyway
- **IF** we change line 469 to use `annotation_select.items()`, the PASS_TO_PASS tests should work

### Evidence

**django/db/models/sql/query.py:469** - Currently uses `self.annotations.items()`:
- `.annotations` contains ALL annotations (`.annotate()` + `.alias()`)
- `.annotation_select` contains only SELECTED annotations (`.annotate()` only)
- Using `.annotations` causes `.alias()` annotations with `contains_aggregate=True` to trigger subqueries

**django/db/models/sql/query.py:508** - Sets mask to all selected annotations:
- `referenced_annotations` is already computed (lines 448-464)
- Should use this instead of `self.annotation_select` to prune unreferenced annotations

**django/db/models/query.py:1664** - `.values()` calls `set_group_by()`:
- This sets `group_by` to a tuple of columns
- Ensures subquery path is taken even if `existing_annotations` is empty
- Prevents PASS_TO_PASS regressions from the `contains_aggregate` filter

### Edit Sites

**File: django/db/models/sql/query.py**

1. **Line 469**: Change from `self.annotations.items()` to `self.annotation_select.items()`
   - This excludes `.alias()` annotations from the subquery decision
   - Keeps the `contains_aggregate` filter to exclude non-aggregate annotations

2. **Line 508**: Change from `self.annotation_select` to `referenced_annotations`  
   - Prunes unreferenced annotations from the inner query
   - `referenced_annotations` is already computed on lines 448-464

### Test Coverage

With these two changes:

**test_unused_aliased_aggregate_pruned** (test #2):
- `.alias()` not in `annotation_select`
- `existing_annotations` = []
- No subquery triggered ✓
- No annotation in SQL ✓

**test_non_aggregate_annotation_pruned** (test #1):  
- Non-aggregate in `annotation_select` but no `contains_aggregate`
- `existing_annotations` = []
- No subquery triggered ✓
- Annotation pruned via line 548 ✓

**test_unreferenced_aggregate_annotation_pruned** (test #3):
- Aggregate in `annotation_select` with `contains_aggregate=True`
- `existing_annotations` = [Count(...)]
- Subquery triggered ✓
- Inner query mask set to `referenced_annotations` = {} ✓
- Annotation NOT in subquery SELECT ✓

**test_referenced_aggregate_annotation_kept** (must still pass):
- `referenced_annotations` = {authors_count}
- Annotation kept in inner query ✓

**PASS_TO_PASS tests** (must not regress):
- `.values()` sets `group_by` to tuple
- Subquery path taken via line 473 check
- Mask not changed (not count() operation)
- All annotations kept ✓


## Craft iteration 1-3 (convergent-stuck)

**Attempted fix:**
1. Line 467: Changed `self.annotations.items()` to `self.annotation_select.items()` ✓ (fixes test #1)  
2. Line ~507: Added conditional logic to set `inner_query.set_annotation_mask(referenced_annotations)` for `.count()` queries in subquery path

**Gate results:**
- Test #1 (test_unused_aliased_aggregate_pruned): PASS
- Test #2 (test_non_aggregate_annotation_pruned): PASS  
- Test #3 (test_unreferenced_aggregate_annotation_pruned): ERROR - SQL syntax error "near 'FROM'"
- PASS_TO_PASS regression: test_aggregation_subquery_annotation_multivalued: ERROR - same SQL syntax error

**Variations tried:**
- Set mask to `referenced_annotations` directly → SQL error
- Add explicit PK to SELECT when `referenced_annotations` is empty → SQL error  
- Only prune aggregate annotations, keep non-aggregates → SQL error

**Evidence:** Setting any annotation mask that excludes aggregate annotations causes "near 'FROM': syntax error" in SQL generation, even when explicitly adding PK to SELECT clause. The safeguard at lines 534-541 that should add PK to empty SELECT is not working, or something else is clearing the SELECT afterward.

**Trajectory:** Convergent-stuck - same SQL syntax error across all attempts to prune via annotation mask.

HYPOTHESIS WRONG: The recon diagnosis assumes pruning via `inner_query.set_annotation_mask(referenced_annotations)` will work, but this breaks SQL generation for queries with GROUP BY. The annotation mask approach may not be compatible with the subquery+GROUP BY setup, or there's a missing step to ensure valid SQL when the mask excludes all annotations. The correct fix may require a different mechanism than the annotation mask, such as processing annotations after the mask is applied or modifying the SQL compiler's handling of masked annotations.

# Audit: django__django-16263

## FAIL_TO_PASS
- test_non_aggregate_annotation_pruned: PASS ✓
- test_unreferenced_aggregate_annotation_pruned: ERROR - `sqlite3.OperationalError: near "FROM": syntax error` at query.py:586 in get_aggregation()
- test_unused_aliased_aggregate_pruned: PASS ✓

## PASS_TO_PASS regressions
- test_aggregation_subquery_annotation_multivalued: ERROR - `sqlite3.OperationalError: near "FROM": syntax error` (confirmed passing in baseline as "ok")
- test_aggregation_default_after_annotation: FAIL - AssertionError: 0 != 40 (expected value not computed)
- test_annotate_values_aggregate: FAIL - AssertionError: 0 != 337 (expected value not computed)

## Pre-existing (not counted, confirmed against base capture)
none

## Kill report

**For RE-ENTER: recon** (1 out of 3 FAIL_TO_PASS still failing indicates the fix is partially effective but the diagnosis missed something):

### Failing FAIL_TO_PASS test
`test_unreferenced_aggregate_annotation_pruned` errors with `sqlite3.OperationalError: near "FROM": syntax error` when executing the count query. The SQL compiler is generating invalid SQL with an empty SELECT clause before FROM.

**Stack trace:**
```
File "/testbed/django/db/models/query.py", line 625, in count
    return self.query.get_count(using=self.db)
File "/testbed/django/db/models/sql/query.py", line 601, in get_count  
    return obj.get_aggregation(using, ["__count"])["__count"]
File "/testbed/django/db/models/sql/query.py", line 586, in get_aggregation
    result = compiler.execute_sql(SINGLE)
```

**What this implicates:**
The patch's annotation pruning logic (via `set_annotation_mask()`) is removing all annotations from the SELECT clause in cases where GROUP BY is present, creating malformed SQL. The subquery path in `get_aggregation()` is setting an annotation mask that results in zero selected fields before the FROM clause.

**Evidence from regressions:**
The SQL syntax error also affects `test_aggregation_subquery_annotation_multivalued` (a PASS_TO_PASS test), suggesting the mask-based pruning approach breaks GROUP BY queries more broadly. The two FAIL assertions (0 vs expected values) indicate annotations that should be included are being incorrectly pruned, causing aggregate calculations to return 0.

**Root cause pattern:**
The annotation mask approach conflicts with Django's SQL compiler requirements for GROUP BY queries. When the mask excludes all annotations but a GROUP BY is present, the compiler generates `SELECT FROM ...` (invalid). The safeguards that should add PK to an empty SELECT (lines 534-541 per hypothesis graph) aren't working, OR the mask is being applied at a stage where those safeguards can't see it.

**Needed for next recon:**
Diagnose why `set_annotation_mask()` produces invalid SQL for GROUP BY queries, or identify an alternative pruning mechanism that doesn't break SQL generation. The fix may need to:
1. Ensure at least PK is selected when mask is empty and GROUP BY is present
2. Prune annotations at a different stage (post-SQL generation?)
3. Use a different mechanism than annotation mask entirely

VERDICT: PARTIAL
RE-ENTER: recon
