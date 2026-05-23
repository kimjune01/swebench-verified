# Hypothesis graph: django__django-11490

## Hypothesis H0: Initial diagnosis
**Mode**: Abduction
**Confidence**: 95% (Deduction - traced through code execution)

**Failure Summary**:
The test `test_union_with_values` checks that calling `values_list()` with different field lists on a union queryset should change the columns returned. The test fails at the assertion:
```
self.assertEqual(reserved_name, (2,))
AssertionError: Tuples differ: ('a', 2, 1) != (2,)
```

Expected: `(2,)` (only the 'order' field)
Got: `('a', 2, 1)` (name, order, id from the previous `values_list()` call)

**Root Cause**:
The SQL compiler modifies query objects in `combined_queries` during SQL compilation, causing state to leak between compilations.

When a union query with `values_select` is compiled (line 428 in `django/db/models/sql/compiler.py`):
```python
if not compiler.query.values_select and self.query.values_select:
    compiler.query.set_values((
        *self.query.extra_select,
        *self.query.values_select,
        *self.query.annotation_select,
    ))
```

The problem: This code modifies `compiler.query` (one of the child queries in `combined_queries`) by calling `set_values()`. Since `combined_queries` contains references to the original query objects (not clones), this modification persists.

**Call Flow**:
1. `qs1 = ReservedName.objects.all()` - creates base queryset
2. `qs1.union(qs1).values_list('name', 'order', 'id').get()`:
   - `union()` creates `combined_queries = (qs1.query, qs1.query)`
   - `values_list()` sets union query's `values_select = ('name', 'order', 'id')`
   - During SQL compilation, `qs1.query.values_select` is empty, so condition is True
   - **Side effect**: `qs1.query.set_values()` is called, modifying `qs1.query` permanently
3. `qs1.union(qs1).values_list('order').get()`:
   - `union()` creates `combined_queries = (qs1.query, qs1.query)` again
   - **But now `qs1.query.values_select` is already `('name', 'order', 'id')`!**
   - `values_list()` sets union query's `values_select = ('order',)`
   - During compilation, condition `if not compiler.query.values_select` is False
   - The `set_values()` is NOT called, so child query keeps old values
   - Query returns wrong columns

**Supporting Evidence**:
- `django/db/models/query.py:934` - `combined_queries` stores direct references:
  ```python
  clone.query.combined_queries = (self.query,) + tuple(qs.query for qs in other_qs)
  ```
- `django/db/models/sql/compiler.py:428-433` - Conditional modification of child queries
- Git commit `0b66c3b4428` added the `if not compiler.query.values_select` check to fix #29286, but introduced this new bug

**Edit Sites**:
- `django/db/models/sql/compiler.py` line 428: Change condition from `if not compiler.query.values_select and self.query.values_select:` to `if self.query.values_select:` to always update child query values when parent has values_select, ensuring they stay in sync even if already set from a previous compilation.

**Confidence Justification**:
This is a deduction (95%+) because I've traced the exact code path and identified the specific line causing the state leak. The bug is deterministic and reproducible.

## Craft Gate Loop

### Iteration 1: Too Broad (Oscillatory Regression)

**Hypothesis**: Remove `not compiler.query.values_select` check to always update values
**Edit**: Changed line 428 from `if not compiler.query.values_select and self.query.values_select:` to `if self.query.values_select:`

**Gate Result**: FAIL_TO_PASS ✓, but regression in test_combining_multiple_models
- Target test `test_union_with_values` passed
- Regression: `test_combining_multiple_models` failed with FieldError: Cannot resolve 'num' into ReservedName
- Trajectory: Oscillatory - fix too broad, applies parent values to children with intentionally different fields from different models

**codex Review**: Predicted this regression - the fix forces parent field names onto child queries from different models that don't have those fields.

### Iteration 2: Clone to Prevent Mutation (Convergent)

**codex Guidance**: Keep original semantic check but clone query before mutation:
```python
if not compiler.query.values_select and self.query.values_select:
    compiler.query = compiler.query.clone()
    compiler.query.set_values((...)
```

**Rationale**:
- `not compiler.query.values_select` guards against overwriting intentional column selections from different models
- Clone prevents mutation of original query objects in `combined_queries`, fixing stale-values bug
- Repeated compilations with different parent values_select now work because we don't mutate the stored child queries

**Edit Applied**:
- Line 428: Restored original condition `if not compiler.query.values_select and self.query.values_select:`
- Line 429: Added `compiler.query = compiler.query.clone()`
- Line 430: `compiler.query.set_values(...)` now operates on the clone

**Gate Result**: ✓ ALL PASS
```
Ran 26 tests in 0.025s
OK (skipped=2)
```

**Status**: RESOLVED
- FAIL_TO_PASS test `test_union_with_values` passes
- All PASS_TO_PASS tests including `test_combining_multiple_models` pass
- Root cause fixed: query mutation prevented by cloning before set_values()


## Audit: django__django-11490

**Patch verified live**:
```
django/db/models/sql/compiler.py | 1 +
```

**Patch content**:
```python
if not compiler.query.values_select and self.query.values_select:
+   compiler.query = compiler.query.clone()
    compiler.query.set_values((
        *self.query.extra_select,
        *self.query.values_select,
```

**Gate execution**: OK (skipped=2)

### FAIL_TO_PASS
- `test_union_with_values`: **PASS** ✓

### PASS_TO_PASS regressions
None — all tests in suite passed.

### Pre-existing failures
None identified. The fail-on-base capture showed 1 failure, but with the patch applied, all tests now pass (0 failures).

### Classification Summary
- **FAIL_TO_PASS**: 1/1 passed ✓
- **PASS_TO_PASS**: 0 regressions ✓
- **Contract fulfilled**: All FAIL_TO_PASS tests pass, zero regressions

The clone() insertion prevents mutation of shared query objects in combined_queries while preserving the original semantic guard that prevents overwriting intentional column selections from different models.

VERDICT: RESOLVED
RE-ENTER: none
