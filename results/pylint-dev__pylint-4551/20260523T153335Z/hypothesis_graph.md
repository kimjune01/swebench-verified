# Hypothesis graph: pylint-dev__pylint-4551

## H₀: Missing type annotation extraction functions
**Type**: Abduction  
**Confidence**: 95% (deduction from test requirements and code structure)

The tests fail because they import functions `get_annotation` and `infer_node` from `pylint.pyreverse.utils`, but these functions don't exist yet.

**Evidence**:
- `tests/unittest_pyreverse_writer.py:32` imports `get_annotation, get_visibility, infer_node`
- ImportError: cannot import name 'get_annotation' from 'pylint.pyreverse.utils'
- `utils.py` currently only has `get_visibility`, missing the other two functions

**Test requirements analysis**:
1. `get_annotation(node)` should:
   - Extract type annotation from AnnAssign nodes (via `node.parent.annotation` when node is a value)
   - Extract type annotation from AssignAttr nodes (via parent function's argument annotations)
   - Wrap non-Optional annotations with `Optional` when default value is `None`
   - Return an object with `.name` attribute

2. `infer_node(node)` should:
   - Try to get annotation first via `get_annotation`
   - Fall back to `node.infer()` if no annotation
   - Handle `astroid.InferenceError` gracefully

**Current type extraction flow**:
- `inspector.py:175-178` - `visit_classdef` calls `handle_assignattr_type` for instance attributes
- `inspector.py:233` - `handle_assignattr_type` uses `node.infer()` to get types
- `inspector.py:221` - `visit_assignname` uses `node.infer()` to get types
- `diagrams.py:88-93` - `get_attrs` displays types from `instance_attrs_type` and `locals_type`

The problem: `node.infer()` infers types from VALUES, not from type ANNOTATIONS.

**Example failure case**:
```python
def __init__(self, a: str = None):
    self.a = a
```
- Current: `node.infer()` sees `None` → infers `NoneType`
- Expected: Should see `a: str` with default `None` → return `Optional[str]`


## Craft iteration 1: Implementation SUCCESS

**Changes applied**:
1. Added `import astroid` to `pylint/pyreverse/utils.py`
2. Added `get_annotation(node)` function that:
   - Handles `AnnAssign` nodes by checking `node.parent`
   - Handles `AssignAttr` nodes by tracing to `__init__` parameter annotations
   - Maps parameter names to annotations using `dict(zip(init_method.locals, init_method.args.annotations))`
   - Detects Optional patterns (startswith, `| None`, `Union[..., None]`, `BinOp` with None)
   - Wraps non-Optional annotations in `Optional[...]` when default value is `None`
   - Sets `.name` attribute on the annotation node with the formatted label
   - Returns the annotation node
3. Added `infer_node(node)` function that:
   - Tries `get_annotation` first
   - Returns `set([annotation])` for Subscript or BinOp nodes
   - Returns `set(ann.infer())` for Name nodes
   - Falls back to `set(node.infer())` if no annotation
   - Catches `InferenceError` and returns `set([ann])` or `set()`
4. Updated `pylint/pyreverse/inspector.py` lines 221 and 233:
   - Changed `values = set(node.infer())` to `values = utils.infer_node(node)`

**Gate result**: ✅ ALL 18 TESTS PASSED
- test_dot_files[packages_No_Name.dot] - PASSED
- test_dot_files[classes_No_Name.dot] - PASSED  
- test_get_visibility (all 4 variants) - PASSED
- test_get_annotation_annassign (all 4 variants) - PASSED
- test_get_annotation_assignattr (all 6 variants) - PASSED
- test_infer_node_1 - PASSED
- test_infer_node_2 - PASSED

**Trajectory**: Convergent success - implementation matches test expectations perfectly.


## Audit: pylint-dev__pylint-4551

### FAIL_TO_PASS
- tests/unittest_pyreverse_writer.py::test_dot_files[packages_No_Name.dot]: PASS ✓
- tests/unittest_pyreverse_writer.py::test_dot_files[classes_No_Name.dot]: PASS ✓
- tests/unittest_pyreverse_writer.py::test_get_visibility[names0-special]: PASS ✓
- tests/unittest_pyreverse_writer.py::test_get_visibility[names1-private]: PASS ✓
- tests/unittest_pyreverse_writer.py::test_get_visibility[names2-public]: PASS ✓
- tests/unittest_pyreverse_writer.py::test_get_visibility[names3-protected]: PASS ✓
- tests/unittest_pyreverse_writer.py::test_get_annotation_annassign[a: str = None-Optional[str]]: PASS ✓
- tests/unittest_pyreverse_writer.py::test_get_annotation_assignattr[def __init__(self, x: str): self.x = x-str]: PASS ✓

All 8 specified FAIL_TO_PASS tests now pass (18 total tests passed in the suite).

### PASS_TO_PASS regressions
none

### Pre-existing (not counted, confirmed against base capture)
none

The baseline showed a complete import failure (`ImportError: cannot import name 'get_annotation'`), preventing all test collection. After the patch, all tests collect and pass.

### Kill report
Not applicable - all FAIL_TO_PASS tests pass, zero regressions.

VERDICT: RESOLVED
RE-ENTER: none
