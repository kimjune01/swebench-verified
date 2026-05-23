# Hypothesis graph: django__django-11555

## H₀: Expression objects passed to get_order_dir (abduction, initial)

**Status**: Active hypothesis
**Reasoning mode**: Deduction
**Confidence**: 95%

### Observation
Test fails with `TypeError: 'OrderBy' object does not support indexing` at `django/db/models/sql/query.py:2221` in `get_order_dir`.

### Call path
1. `ChildArticle.objects.order_by('article_ptr')` - order by parent pointer
2. `get_order_by()` processes 'article_ptr' string
3. `find_ordering_name('article_ptr', ...)` at compiler.py:330
4. Detects field is a relation with ordering (article_ptr → Article)
5. Recursively calls `find_ordering_name(item, ...)` for each item in Article's `Meta.ordering`
6. Article.ordering contains expressions: `F('author__name').asc()`, `OrderBy(F('second_author__name'))`
7. Expression objects passed as `name` parameter to `find_ordering_name`
8. Line 707: `get_order_dir(name, default_order)` called where `name` is OrderBy object
9. Line 2221: `get_order_dir` tries `field[0]` which fails on expression objects

### Root cause
`find_ordering_name` (compiler.py:707) calls `get_order_dir` without checking if `name` is an expression object. The function assumes `name` is always a string field name, but during recursive processing of parent model ordering with expressions, it receives OrderBy/F objects.

### Supporting evidence
- `django/db/models/sql/compiler.py:707` - unconditional call to `get_order_dir(name, default_order)`
- `django/db/models/sql/compiler.py:281-291` - parallel code in `get_order_by` that correctly handles expressions with `if hasattr(field, 'resolve_expression')` check before calling `get_order_dir`
- `django/db/models/sql/query.py:2221` - `get_order_dir` assumes string: `if field[0] == '-'`
- `tests/ordering/models.py:34-37` - Article.Meta.ordering contains expression objects

### Edit site
**File**: `django/db/models/sql/compiler.py`
**Function**: `find_ordering_name`
**Lines**: 700-710

Add check after docstring (before line 707):
```
if hasattr(name, 'resolve_expression'):
    # name is already an expression (F(), OrderBy, etc.)
    if not isinstance(name, OrderBy):
        name = name.asc()
    if not self.query.standard_ordering:
        name = name.copy()
        name.reverse_ordering()
    return [(name, False)]
```

This mirrors the pattern in `get_order_by` at lines 282-291.


## Craft Gate Loop

### Iteration 1: Draft & Volley

**Drafted fix**: Added expression check at top of `find_ordering_name` (before `get_order_dir` call at line 707)

**Codex feedback**:
- ❌ Wrong placement: early return ignores alias/opts/name context
- ❌ Expressions need to be resolved relative to related model, not blindly returned
- ❌ Skips recursive machinery that handles path-aware treatment
- ✓ OrderBy already imported (line 8)
- **Guidance**: Fix should be inside the branch that expands `opts.ordering` (lines 724-726), not at the function top

**Revised fix**: Moved check inside the `for item in opts.ordering` loop at line 724, handling expressions before recursive call

**Codex approval**:
- ✓ Correct placement: intercepts expressions only during opts.ordering expansion
- ✓ Avoids calling `get_order_dir` on expression objects
- ✓ Respects `descending` parameter for order direction
- ✓ Handles both `F().asc()` and `OrderBy()` expressions
- Refinement: Use existing `descending` variable instead of checking `order == 'DESC'`

**Applied**: 
```python
# In find_ordering_name at line 724, inside "for item in opts.ordering:"
if hasattr(item, 'resolve_expression'):
    if not isinstance(item, OrderBy):
        item = item.desc() if descending else item.asc()
    elif descending:
        item = item.copy()
        item.reverse_ordering()
    results.append((item, False))
    continue
```

**Gate result**: ✅ GREEN
- All 27 tests passed
- `test_order_by_ptr_field_with_default_ordering_by_expression` ✓ PASS
- No PASS_TO_PASS regressions

**Trajectory**: Convergent success (one-shot resolution)

## Audit: django__django-11555

### Phase 1: Patch verification
```
git diff --stat
 django/db/models/sql/compiler.py | 9 +++++++++
 1 file changed, 9 insertions(+)
```
Patch is live.

### Phase 2: Gate execution
Ran full test suite via `/tmp/gate-django_django-11555`:
- 27 tests executed
- All tests passed
- Runtime: 0.058s

### Phase 3: Classification against baseline

#### FAIL_TO_PASS
- `test_order_by_ptr_field_with_default_ordering_by_expression`: **PASS** ✓
  - Baseline: ERROR (TypeError: 'OrderBy' object does not support indexing)
  - Current: PASS
  - **Fix successful**

#### PASS_TO_PASS
All 26 PASS_TO_PASS tests remain passing:
- `test_default_ordering` ✓
- `test_default_ordering_by_f_expression` ✓
- `test_default_ordering_override` ✓
- `test_deprecated_values_annotate` ✓
- `test_extra_ordering` ✓
- `test_extra_ordering_quoting` ✓
- `test_extra_ordering_with_table_name` ✓
- `test_no_reordering_after_slicing` ✓
- `test_order_by_constant_value` ✓
- `test_order_by_constant_value_without_output_field` ✓
- `test_order_by_f_expression` ✓
- `test_order_by_f_expression_duplicates` ✓
- `test_order_by_fk_attname` ✓
- `test_order_by_nulls_first` ✓
- `test_order_by_nulls_first_and_last` ✓
- `test_order_by_nulls_last` ✓
- `test_order_by_override` ✓
- `test_order_by_pk` ✓
- `test_orders_nulls_first_on_filtered_subquery` ✓
- `test_random_ordering` ✓
- `test_related_ordering_duplicate_table_reference` ✓
- `test_reverse_meta_ordering_pure` ✓
- `test_reverse_ordering_pure` ✓
- `test_reversed_ordering` ✓
- `test_stop_slicing` ✓
- `test_stop_start_slicing` ✓

**Regressions**: None

#### Pre-existing failures
None counted. The single pre-existing failure (`test_order_by_ptr_field_with_default_ordering_by_expression`) is now resolved.

### Phase 4: Verdict

✅ **Contract fulfilled**:
- All FAIL_TO_PASS tests now pass (1/1)
- Zero PASS_TO_PASS regressions (0/26)
- Gate is green

The fix correctly intercepts expression objects during `opts.ordering` expansion in `find_ordering_name`, preventing the TypeError when ordering by a pointer field that references a model with expression-based default ordering.

VERDICT: RESOLVED
RE-ENTER: none
