# Hypothesis graph: pydata__xarray-4629

## H₁: merge_attrs with combine_attrs='override' returns dict reference instead of copy
**Status**: Active  
**Mode**: Deduction (95%)  
**Evidence**:
- Test failure: `xarray/tests/test_merge.py::TestMergeFunction::test_merge_attrs_override_copy`
  - Modifying `ds3.attrs["x"]` after merge changes `ds1.attrs["x"]` 
  - Expected ds1.x == 0, got ds1.x == 2
- Root cause: `xarray/core/merge.py:504` returns `variable_attrs[0]` directly
  - This returns the original dict reference from the first object
  - Other branches ("no_conflicts", "identical") use `dict(variable_attrs[0])` to create a copy
- Supporting code:
  ```python
  # xarray/core/merge.py:503-505
  elif combine_attrs == "override":
      return variable_attrs[0]  # <- returns reference, not copy
  
  # Compare to:
  # xarray/core/merge.py:506-507
  elif combine_attrs == "no_conflicts":
      result = dict(variable_attrs[0])  # <- creates copy
  ```

**Edit site**: `xarray/core/merge.py:504`  
**Fix**: Change `return variable_attrs[0]` to `return dict(variable_attrs[0])`

## Gate loop

### Iteration 1: Initial fix applied
**Change**: `xarray/core/merge.py:504` — `return variable_attrs[0]` → `return dict(variable_attrs[0])`

**codex review (pre-gate)**: 
- Confirms fix addresses the stated bug
- Notes this is a shallow copy (consistent with other branches)
- dict() drops custom mapping subclass identity (matches existing "no_conflicts" and "identical" branches)
- Regression test already exists (test_merge_attrs_override_copy is the FAIL_TO_PASS test)

**Gate result**: ✅ PASS  
All 33 tests in `xarray/tests/test_merge.py` passed, including:
- `test_merge_attrs_override_copy` (FAIL_TO_PASS) ✅

**Trajectory**: Convergent (resolved) — single minimal edit resolved the issue on first gate run.


---
# Audit: pydata__xarray-4629

## FAIL_TO_PASS
- test_merge_attrs_override_copy: PASSED ✓

## PASS_TO_PASS regressions
None

## Pre-existing (not counted, confirmed against base capture)
None

## Summary
The craft patch correctly fixes the attrs copy issue by changing line 504 in xarray/core/merge.py from:
```python
return variable_attrs[0]
```
to:
```python
return dict(variable_attrs[0])
```

This ensures that when `combine_attrs="override"`, the returned attrs dict is a copy rather than a reference to the original, preventing inadvertent mutation of source dataset attrs when the merged result is modified.

All 33 tests passed. No regressions introduced.

VERDICT: RESOLVED
RE-ENTER: none
