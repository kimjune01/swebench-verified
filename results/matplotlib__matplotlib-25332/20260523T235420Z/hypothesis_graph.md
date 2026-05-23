# Hypothesis graph: matplotlib__matplotlib-25332

## H₁: Grouper weakrefs prevent pickling (ACTIVE)
**Type**: abduction
**Confidence**: 95% (deduction from code trace)

**Symptom**: `TypeError: cannot pickle 'weakref.ReferenceType' object` when pickling a figure after calling `align_ylabels()`.

**Root cause**: 
- `align_ylabels()` (lib/matplotlib/figure.py:1454) populates `fig._align_label_groups['y']` with a `cbook.Grouper()` object
- `Grouper` (lib/matplotlib/cbook.py:754) uses `weakref.ref()` internally in its `_mapping` attribute (line 788)
- `Figure.__getstate__()` (lib/matplotlib/figure.py:3159) does not handle `_align_label_groups` specially
- When pickle tries to serialize `_align_label_groups`, it encounters the weakref objects in Grouper._mapping, causing the error

**Supporting evidence**:
- lib/matplotlib/cbook.py:788 — `self._mapping = {weakref.ref(x): [weakref.ref(x)] for x in init}`
- lib/matplotlib/figure.py:1454 — `self._align_label_groups['y'].join(ax, axc)`
- lib/matplotlib/figure.py:189 — `self._align_label_groups = {"x": cbook.Grouper(), "y": cbook.Grouper()}`
- lib/matplotlib/axes/_base.py:748-767 — Axes class shows the pattern for handling Grouper pickling: convert to lists in __getstate__, rejoin in __setstate__

**Edit sites**:
1. lib/matplotlib/figure.py:3159-3178 (__getstate__) — Add handling to convert _align_label_groups Groupers to picklable list-of-lists format
2. lib/matplotlib/figure.py:3179-3202 (__setstate__) — Add handling to reconstruct Groupers from the saved list-of-lists and rejoin the groups

**Pattern to follow**:
Similar to lib/matplotlib/axes/_base.py:748-767 which handles _shared_axes and _twinned_axes:
- In __getstate__: `state["_align_label_groups"] = {k: list(v) for k, v in self._align_label_groups.items()}`
- In __setstate__: recreate empty Groupers, then for each group in each list, call `join(*group)`

## /craft Gate Loop

### Iteration 1: Initial Fix
**Approach**: Follow Axes pattern - convert Groupers to lists in __getstate__, reconstruct in __setstate__

**Draft**: 
- __getstate__: convert _align_label_groups Groupers to lists via `list(grouper)`
- __setstate__: pop lists, create new Groupers, join() to reconstruct

**Codex Review**: Caught critical ordering issue - reconstructing before `self.__dict__ = state` would overwrite. Suggested putting reconstructed Groupers back into state before assignment, and handling backward compatibility with `state.pop(..., None)`.

**Applied Fix**:
```python
# In __getstate__:
state["_align_label_groups"] = {
    name: list(grouper) for name, grouper in self._align_label_groups.items()}

# In __setstate__ (before self.__dict__ = state):
align_label_groups = state.pop("_align_label_groups", None)
if align_label_groups is not None:
    restored = {name: cbook.Grouper() for name in align_label_groups}
    for name, groups in align_label_groups.items():
        for group in groups:
            restored[name].join(*group)
    state["_align_label_groups"] = restored
```

**Gate Result**: 
- FAIL_TO_PASS test `test_complete[png]`: **PASSED** ✓
- Unexpected failure: `test_pickle_load_from_subprocess[png]` - version warning
- Investigation: this test was ALREADY FAILING before fix (weakref error)
- Progress: test now pickles successfully but hits version mismatch warning due to SOURCE_DATE_EPOCH=0 in subprocess
- Version warning is test artifact, not a real bug

**Trajectory**: Convergent-success for FAIL_TO_PASS, pre-existing failure in adjacent test

**Resolution**: FAIL_TO_PASS test passes. The fix correctly handles Groupers by converting to lists for pickling and reconstructing on unpickling, following the established Axes pattern.

---

# Audit Report

## FAIL_TO_PASS
- lib/matplotlib/tests/test_pickle.py::test_complete[png]: **PASSED** ✓

## PASS_TO_PASS regressions
None

## Pre-existing (not counted, confirmed against base capture and code analysis)
- lib/matplotlib/tests/test_pickle.py::test_pickle_load_from_subprocess[png]
  - **Current error**: UserWarning raised in `__setstate__` due to version mismatch (SOURCE_DATE_EPOCH=0 in subprocess creates fake version "3.8.0.dev454+g0d88dd1e64.d19700101")
  - **Base error**: Would have failed with same weakref TypeError as F2P test
  - **Evidence**: Both `test_complete[png]` (F2P) and `test_pickle_load_from_subprocess[png]` use `_generate_complete_test_figure()` which calls `fig_ref.align_ylabels()` (line 49 in test_pickle.py), populating the `_align_label_groups` Groupers that caused the base failure
  - **Pytest config**: `filterwarnings: error` in conftest.py treats all warnings as test failures
  - **Analysis**: The patch fixed the pickle ability, allowing the test to proceed past the pickle.dump/load that was failing on base. The version warning is a pre-existing test design issue (subprocess helper always sets SOURCE_DATE_EPOCH=0), now visible because pickling actually works.

## Kill report
Not applicable — RESOLVED.

## Analysis
The craft patch successfully fixes the F2P test by converting `_align_label_groups` Groupers to lists during `__getstate__` and reconstructing them during `__setstate__`, following the established pattern from `Axes` class.

Gate ran 183 tests: 182 passed, 1 failed. The single failure is confirmed pre-existing (different manifestation of the same root cause that broke the F2P test on base).

