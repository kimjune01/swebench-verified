# Hypothesis graph: django__django-10554

## H₀: Initial symptom (abduction)
Tests fail with: `DatabaseError: ORDER BY term does not match any column in the result set.`
- Raised at `django/db/models/sql/compiler.py:359` in `get_order_by()`
- Occurs when using `.union().order_by().values_list()` or `.union().values_list().order_by()`

## H₁: Root cause (deduction - 95%)
When a UNION queryset combines `.values_list('order')` (limiting SELECT) with `.order_by('pk')` (ordering by different column):

1. `get_order_by()` tries to convert ORDER BY to positional references (e.g., `ORDER BY 1`) for SQL UNION compatibility
2. It loops through `self.select` (line 350) to find 'pk', but SELECT only contains 'order'
3. Loop completes without match → raises DatabaseError at line 359

**Why this matters:** SQL UNION requires ORDER BY columns to be in the SELECT list. Django handles this for DISTINCT queries via `get_extra_select()` (lines 374-380), but NOT for combinator queries.

**Supporting evidence:**
- `django/db/models/sql/compiler.py:374` - condition only checks `self.query.distinct`, not `self.query.combinator`
- `django/db/models/sql/compiler.py:350-359` - matching loop has no fallback to add missing columns
- Original UNION implementation (commit 84c1826ded) included this error but didn't account for values_list edge case

## Edit sites

**Primary:** `django/db/models/sql/compiler.py` lines 350-359 (in combinator section of `get_order_by()`)
- When ORDER BY column not found in SELECT, add it to `self.select` instead of raising error
- Then perform positional conversion

**Secondary check:** `django/db/models/sql/compiler.py` lines 428-433 (`get_combinator_sql()`)
- Verify added columns propagate to combined queries via values_select mechanism

## Gate Loop Node - /craft iteration 1

**Iteration 1 - Initial fix attempt**
- Applied simple fix: append ORDER BY column to `self.select` when not found
- **Gate result**: `OperationalError: 1st ORDER BY term out of range - should be between 1 and 1`
- **Trajectory**: Divergent (progress) - column added to parent but not propagated to child queries
- **Analysis**: codex correctly warned that appending to `self.select` alone doesn't propagate to UNION child queries

**Iteration 2 - Annotation propagation**
- Volleyed with codex: suggested using `annotation_select` via `Query.add_annotation()`
- Added hidden annotation (`__orderbycol1`) to both parent and all combined queries
- **Gate result**: `FAILED (failures=1)` - `test_order_raises_on_non_selected_column` failed
- **Trajectory**: Oscillatory (regression) - FAIL_TO_PASS tests passed but broke existing test
- **Analysis**: Fix was too broad - it added ORDER BY columns even when child queries already had incompatible `.values()` selections

**Iteration 3 - Conditional annotation** 
- Added conditional check: only add ORDER BY column if child queries don't already have `values_select`
- Logic: `if not any(q.values_select for q in self.query.combined_queries):`
- **Gate result**: `OK (skipped=2)` - All 27 tests pass
- **Trajectory**: Convergent (success)

**Final fix location**: `django/db/models/sql/compiler.py:359-375`

**Key insight**: The fix must distinguish between:
1. `.values()` on individual queries before UNION (incompatible columns) → raise error
2. `.values_list()` on UNION result (compatible columns) → add ORDER BY column

The conditional check achieves this by only adding columns when `values_select` is propagated from parent to children (case 2), not when children already have their own `values_select` (case 1).

**Volley count**: 3 (draft review, propagation error, regression analysis)
**Gate iterations**: 3
**Result**: RESOLVED

## Audit verification

**Patch status**: Live in tree
```
django/db/models/sql/compiler.py | 18 +++++++++++++++++-
1 file changed, 17 insertions(+), 1 deletion(-)
```

**Gate result**: OK (skipped=2) - 27 tests ran in 0.026s

### FAIL_TO_PASS results
- `test_union_with_values_list_and_order`: **PASS** ✓
- `test_union_with_values_list_on_annotated_and_unannotated`: **PASS** ✓

### PASS_TO_PASS regressions
None - all 25 PASS_TO_PASS tests continue to pass.

### Pre-existing failures (baseline)
The fail-on-base capture showed the test suite crashed with `Traceback (most recent call last): File "./tests/runtests.py", line 564` before completing. With the patch applied, the full suite runs cleanly.

### Verdict analysis
✓ All FAIL_TO_PASS tests now pass  
✓ Zero PASS_TO_PASS regressions  
✓ Clean gate run with no errors

The patch successfully resolves the issue by conditionally adding ORDER BY columns to UNION queries when:
1. The ORDER BY column is not in the SELECT list
2. Child queries don't already have their own `values_select` (avoiding conflicts)

This allows `.union().order_by().values_list()` patterns to work while preserving the error for incompatible mixed-values cases.

