# Hypothesis graph: django__django-15957

## H1: get_prefetch_queryset methods call filter() on sliced querysets
**Type**: abduction  
**Confidence**: 95% (deduction from code trace)

**Evidence**:
- Stack trace shows `TypeError: Cannot filter a query once a slice has been taken.` at:
  - `/testbed/django/db/models/fields/related_descriptors.py:722` (ReverseManyToOneDescriptor.get_prefetch_queryset)
  - `/testbed/django/db/models/fields/related_descriptors.py:1055` (ManyToManyDescriptor.get_prefetch_queryset)
- `/testbed/django/db/models/query.py:1442` raises this error when `self.query.is_sliced` is True
- The `get_prefetch_queryset` methods receive a sliced queryset and attempt to filter it

**Root cause**:
When Prefetch objects contain sliced querysets (e.g., `authors[1:]`), the prefetch mechanism needs to filter these querysets to match the instances being prefetched. However, all four `get_prefetch_queryset` methods in `related_descriptors.py` call `.filter(**query)` directly on the passed queryset without checking if it's already sliced. Django prohibits filtering after slicing because the SQL semantics are ambiguous (should the filter apply before or after the slice?).

**Edit sites**:
- `django/db/models/fields/related_descriptors.py` line ~124 (ForwardManyToOneDescriptor.get_prefetch_queryset)
- `django/db/models/fields/related_descriptors.py` line ~398 (ReverseOneToOneDescriptor.get_prefetch_queryset)
- `django/db/models/fields/related_descriptors.py` line ~722 (ReverseManyToOneDescriptor.get_prefetch_queryset)
- `django/db/models/fields/related_descriptors.py` line ~1055 (ManyToManyDescriptor.get_prefetch_queryset)

**Fix approach**:
Before calling `.filter()`, check if `queryset.query.is_sliced`. If true:
1. Save the slice bounds: `low_mark = queryset.query.low_mark`, `high_mark = queryset.query.high_mark`
2. Clear the slice: `queryset.query.clear_limits()`
3. Apply the filter: `queryset = queryset.filter(**query)`
4. Re-apply the slice: `queryset.query.set_limits(low=low_mark, high=high_mark)`

This ensures the filter is applied before the slice in the SQL query.

## Craft Iteration 1

**Attempt**: Applied slice handling to all four `get_prefetch_queryset` methods:
- Save low_mark/high_mark
- Clear limits
- Apply filter (and extra() for M2M)
- Restore limits

**Gate Result**: FAILED (8 failures, 0 errors)
- All tests run without exceptions now (no more "Cannot filter/change a query once a slice has been taken")
- But tests return wrong results - slices being lost or applied incorrectly
- Example: `test_m2m_forward (book 2)` expects `[]` but gets `[<Author: Charlotte>]`

**Hypothesis**: The slice restoration might not be working correctly. Need to verify that `set_limits()` actually modifies the query properly after `extra()` has been called, or check if there's an issue with how the query object is being manipulated.


## Craft Iteration 2-3

**Multiple attempts** with different approaches to restore the slice:
- Direct attribute assignment (`queryset.query.low_mark = low_mark`)
- Using queryset slicing syntax (`queryset[low_mark:high_mark]`)

**Gate Result**: Still FAILED (8 failures)
- Same wrong results persisting

**Key Insight**: The fundamental issue is that prefetch fetches ALL related objects in ONE query, then distributes them to instances. When we apply a slice to the queryset in SQL, it slices the ENTIRE result set across all instances, not per-instance.

Example:
- Book 1 → Authors [A, B, C], want [1:] = [B, C]
- Book 2 → Authors [D], want [1:] = []

After filter: [A, B, C, D]
After slice [1:]: [B, C, D]
Distribution gives Book 1 → [B, C] ✓, Book 2 → [D] ✗ (should be [])

**Conclusion**: The recon diagnosis approach is wrong. The slice cannot be applied in the SQL query in `get_prefetch_queryset`. It needs to be applied AFTER results are distributed to each instance, which happens elsewhere in Django's prefetch machinery.

**Status**: NOT-RESOLVED — re-diagnose

The fix location is not in `get_prefetch_queryset` methods. Need to find where prefetch results are distributed to instances and apply per-instance slicing there.


## H2: Slice must be applied per-instance during result distribution

**Type**: deduction  
**Confidence**: 95%

**Evidence**:
- The tests pass without exceptions, but produce wrong results
- Test failures show global slice behavior:
  - `test_m2m_forward (book 2)`: expects `[]` (1: slice of single author), gets `[<Author: Charlotte>]`
  - Pattern shows slice `[1:]` applied to ALL authors across all books, not per-book
- Code trace in `django/db/models/query.py:2470`: `all_related_objects = list(rel_qs)` executes the sliced query globally
- Line 2472-2474: Results grouped into `rel_obj_cache` by instance ID
- Line 2501: `vals = rel_obj_cache.get(instance_attr_val, [])` retrieves per-instance results
- Line 2520/2528: `vals` assigned to instance

**Root cause**:
Prefetch works by:
1. Fetching ALL related objects across all instances in ONE SQL query
2. Grouping results by instance ID into `rel_obj_cache`
3. Distributing grouped results to each instance

When a slice is applied in SQL (in `get_prefetch_queryset`), it slices the entire global result set, not per-instance. Example:
- Book 1 has authors [A, B, C], slice `[1:]` should give [B, C]
- Book 2 has authors [D], slice `[1:]` should give []
- Combined query fetches [A, B, C, D]
- SQL slice `[1:]` gives [B, C, D] (wrong! - global slice, not per-instance)
- Distribution: Book 1 gets [B, C] ✓, Book 2 gets [D] ✗

The slice must be applied to `vals` for EACH instance, not to the combined queryset.

**Edit sites**:

1. **django/db/models/fields/related_descriptors.py, lines 151-161** (ForwardManyToOneDescriptor.get_prefetch_queryset):
   - Remove the slice reapplication code (lines 158-161)
   - Keep the slice clearing (lines 151-153) so ALL related objects are fetched

2. **django/db/models/fields/related_descriptors.py, lines 427-433** (ReverseOneToOneDescriptor.get_prefetch_queryset):
   - Remove the slice reapplication code
   - Keep the slice clearing

3. **django/db/models/fields/related_descriptors.py, lines 750-757** (ReverseManyToOneDescriptor.get_prefetch_queryset):
   - Remove the slice limit restoration (lines 755-757)
   - Keep the slice clearing (lines 751-753)

4. **django/db/models/fields/related_descriptors.py, lines 1095-1126** (ManyToManyDescriptor.get_prefetch_queryset):
   - Remove the slice reapplication code (lines 1121-1126)
   - Keep the slice clearing (lines 1095-1097)

5. **django/db/models/query.py, lines 2498-2530** (prefetch_one_level distribution loop):
   - After line 2501 (`vals = rel_obj_cache.get(instance_attr_val, [])`), add logic to:
     - Check if `lookup.queryset` is not None and is sliced
     - If sliced, extract `low_mark` and `high_mark` from `lookup.queryset.query`
     - Apply the slice to `vals`: `vals = vals[low_mark:high_mark]`
   - This applies the slice per-instance during distribution

**Supporting code quotes**:

`django/db/models/fields/related_descriptors.py:1095-1126`:
```python
was_sliced = queryset.query.is_sliced
if was_sliced:
    low_mark, high_mark = queryset.query.low_mark, queryset.query.high_mark
    queryset.query.clear_limits()

queryset = queryset.filter(**query)
# ... extra() call ...

if was_sliced:
    # Reapply the slice using queryset slicing syntax
    if high_mark is None:
        queryset = queryset[low_mark:]
    else:
        queryset = queryset[low_mark:high_mark]
```
This reapplication is WRONG - it slices globally. Must be removed.

`django/db/models/query.py:2498-2520`:
```python
for obj in instances:
    instance_attr_val = instance_attr(obj)
    vals = rel_obj_cache.get(instance_attr_val, [])
    # <-- INSERT PER-INSTANCE SLICE HERE

    if single:
        val = vals[0] if vals else None
        # ... assignment ...
    else:
        if as_attr:
            setattr(obj, to_attr, vals)  # <-- vals used here
```

The slice must be applied to `vals` BEFORE the assignment logic.


## Craft Iteration 1 (window function approach)

**Fix implemented**: Created `_filter_prefetch_queryset` helper function that uses window functions (ROW_NUMBER() OVER PARTITION BY) to apply slices per-parent in SQL, rather than globally. Updated `ReverseManyToOneDescriptor.get_prefetch_queryset` and `ManyToManyDescriptor.get_prefetch_queryset` to use this helper.

**Key changes**:
1. Added `_filter_prefetch_queryset(queryset, field_name, instances)` helper in `related_descriptors.py`
2. Helper converts slices to window function predicates:
   - `Window(RowNumber(), partition_by=field_name, order_by=queryset_order)`
   - `predicate &= GreaterThan(window, low_mark)`
   - `predicate &= LessThanOrEqual(window, high_mark)` if high_mark exists
   - Clears SQL limits and applies the window predicate
3. ReverseManyToOne (line ~742): replaced manual filter with helper call
4. M2M (line ~1078): replaced slice clearing/restoration logic with helper call

**Gate Result**: PASS (93/93 tests, 0.230s)
All FAIL_TO_PASS tests now pass:
- test_foreignkey_reverse
- test_m2m_forward  
- test_m2m_reverse
- test_reverse_ordering

No regressions.

**Resolution**: RESOLVED — window function approach correctly applies slices per-instance using SQL PARTITION BY.
