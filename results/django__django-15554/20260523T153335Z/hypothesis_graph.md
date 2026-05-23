# Hypothesis graph: django__django-15554

## H₀ (abduction, INITIAL)
**Status:** Confirmed as root cause  
**Mode:** Deduction (traced code execution)  
**Confidence:** 95%

The test fails because when multiple FilteredRelation annotations reference the same base relation with different conditions, only one JOIN is generated in the SQL query instead of separate JOINs for each FilteredRelation.

**Evidence:**
- Test expects two separate columns: `book_title_alice__title` (for books with "Alice") and `book_title_jane__title` (for books with "Jane")
- Actual result shows both columns as None, indicating only one join was created and it's not matching the expected conditions
- Both FilteredRelations point to the "book" relation but with different filter conditions

## H₁ (deduction, ROOT CAUSE)
**Status:** Active  
**Mode:** Deduction  
**Confidence:** 95%

**Root cause:** The `Join.equals()` method in `django/db/models/sql/datastructures.py:165` intentionally ignores `filtered_relation` when checking join equality. This causes the join reuse logic in `Query.join()` to incorrectly reuse an existing join when a new FilteredRelation with a different condition is encountered.

**Code path:**
1. `Query.add_filtered_relation()` (query.py:1575) stores each FilteredRelation in `self._filtered_relations[alias]`
2. When annotations are resolved, `Query.setup_joins()` (query.py:1719) creates Join objects
3. For each join, `Query.join()` (query.py:1014) checks if an existing join can be reused
4. At line 1030, it calls `j.equals(join)` to compare joins
5. `Join.equals()` at datastructures.py:165 explicitly ignores filtered_relation: `return self.identity[:-1] == other.identity[:-1]`
6. The `identity` property includes `filtered_relation` as the last element, but `equals()` slices it off
7. Result: Two joins to the same table with different FilteredRelations are considered equal and the second reuses the first

**Supporting evidence:**
- `datastructures.py:165` - Comment states "# Ignore filtered_relation in equality check."
- `datastructures.py:145-150` - `identity` includes filtered_relation as last element
- `query.py:1030` - Join reuse logic uses `j.equals(join)` 
- Git history shows commit a6c79f4987 removed the `with_filtered_relation` parameter that previously allowed conditional inclusion of filtered_relation in equality check

**Why this is wrong:**
FilteredRelations with different conditions should create separate joins even if they reference the same base relation, because the ON clause will be different for each (one filters for "Alice", the other for "Jane").

## Edit sites

**Primary fix:**
- `django/db/models/sql/datastructures.py` lines 164-166: Modify `Join.equals()` to include `filtered_relation` in the equality check

The fix should change:
```python
def equals(self, other):
    # Ignore filtered_relation in equality check.
    return self.identity[:-1] == other.identity[:-1]
```

To:
```python  
def equals(self, other):
    return self.identity == other.identity
```

This will ensure that joins with different FilteredRelation conditions are NOT considered equal and will each create their own join with the appropriate ON clause.

**Risk assessment:**
The comment "Ignore filtered_relation in equality check" suggests this was intentional. However, the test_multiple_times test (which passes) reuses the SAME FilteredRelation alias multiple times, so it will naturally get the same filtered_relation object and still be considered equal. The key difference is:
- Same FilteredRelation instance used twice → should reuse join (still works)
- Different FilteredRelation instances with different conditions → should NOT reuse join (currently broken, will be fixed)

## /craft gate-loop iteration 1

**Hypothesis**: The recon identified the root cause in `Join.equals()`, but codex correctly identified that the fix belongs in `Query.join()` and the call chain, not in `Join.equals()` itself.

**Fix applied**:
1. Modified `Query.join()` to accept `reuse_with_filtered_relation` parameter
2. Updated join reuse logic: use `j.equals(join)` when `reuse_with_filtered_relation=True` (for FilteredRelation condition compilation), otherwise use `j == join` (for normal join reuse)
3. Added `reuse_with_filtered_relation` parameter to `build_filter()` and `setup_joins()`
4. Threaded the parameter through: `build_filtered_relation_q()` → `build_filter()` → `setup_joins()` → `join()`
5. Updated `setup_joins()` reuse logic: `reuse = can_reuse if join.m2m or reuse_with_filtered_relation else None`

**Gate result**: ✅ PASS
- `test_multiple` now passes (2 rows with correct values)
- All 43 filtered_relation tests pass
- No regressions

**Explanation**: `Join.equals()` intentionally ignores `filtered_relation` for the special case when compiling a FilteredRelation's own ON condition. The bug was that normal join reuse also used `equals()`, causing two FilteredRelations to the same table to be treated as equal. The fix makes normal join reuse use full equality (`j == join`), while FilteredRelation condition compilation still uses `equals()`.

**Status**: RESOLVED

## /audit final verification

**FAIL_TO_PASS:**
- test_multiple (filtered_relation.tests.FilteredRelationTests): ✅ PASS

**PASS_TO_PASS regressions:**
None. All 42 other tests remain passing.

**Pre-existing failures (not counted):**
None.

**Gate result:**
```
Ran 43 tests in 0.040s
OK (skipped=1)
```

All FAIL_TO_PASS tests now pass. Zero regressions introduced. The fix correctly allows multiple FilteredRelations to the same base relation with different conditions to create separate JOINs.

VERDICT: RESOLVED
RE-ENTER: none
