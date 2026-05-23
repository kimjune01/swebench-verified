# Hypothesis graph: sympy__sympy-17655

## Hypothesis H0 (abduction)
**Date**: 2026-05-23
**Type**: Root cause identified

The tests fail because the `Point` class defines `__mul__` for right multiplication (Point * scalar) but does not define `__rmul__` for left multiplication (scalar * Point).

When Python evaluates `5 * p4`:
1. Python first tries `(5).__mul__(p4)` - the int doesn't know how to multiply with a Point
2. Python then tries `p4.__rmul__(5)` - but Point doesn't have this method
3. This raises `TypeError: unsupported operand type(s) for *: 'int' and 'Point2D'`

Conversely, `p4 * 5` works because:
1. Python tries `p4.__mul__(5)` - this exists and works correctly

**Evidence**:
- `sympy/geometry/point.py:250` - `__mul__` method exists
- No `__rmul__` method anywhere in the file (grep returns 0 matches)
- Error message: `TypeError: unsupported operand type(s) for *: 'int' and 'Point2D'`

**Fix**: Add `__rmul__` method that delegates to `__mul__` (since scalar multiplication is commutative)

**Confidence**: Deduction - 99% (traced through Python's operator resolution mechanism and verified code)

## Craft gate-loop

### Iteration 1: Initial fix

**Action**: Added `__rmul__` method to Point class (sympy/geometry/point.py:281-284)
```python
def __rmul__(self, factor):
    """Multiply point's coordinates by a factor (left multiplication)."""
    return self.__mul__(factor)
```

**Codex pre-gate review**: "Patch fixes the two failing tests for normal scalar values. The noncommutative ordering caveat is unlikely to matter for these geometry tests. Proposed patch is probably sufficient."

**Gate result**: ✅ PASS
- test_point: ok
- test_point3D: ok
- All 12 tests in test_point.py passed

**Resolution**: FAIL_TO_PASS tests pass. Fix complete.

## Audit: sympy__sympy-17655

**Date**: 2026-05-23
**Phase**: Regression verification

### FAIL_TO_PASS Results
- test_point: **PASS** ✅ (was E on base: `TypeError: unsupported operand type(s) for *: 'int' and 'Point2D'`)
- test_point3D: **PASS** ✅ (was E on base: `TypeError: unsupported operand type(s) for *: 'int' and 'Point3D'`)

### PASS_TO_PASS Results
- test_Point2D: PASS ✅
- test_issue_9214: PASS ✅
- test_issue_11617: PASS ✅
- test_transform: PASS ✅
- test_concyclic_doctest_bug: PASS ✅
- test_arguments: PASS ✅
- test_unit: PASS ✅
- test_dot: PASS ✅
- test__normalize_dimension: PASS ✅

**Regressions**: none

### Pre-existing failures (not counted)
none

### Gate output
```
============================= test process starts ==============================
executable:         /opt/miniconda3/envs/testbed/bin/python  (3.9.20-final-0) [CPython]
architecture:       64-bit
cache:              no
ground types:       python 
numpy:              None
random seed:        42078130
hash randomization: on (PYTHONHASHSEED=3402786913)

sympy/geometry/tests/test_point.py[12] 
test_point ok
test_point3D ok
test_Point2D ok
test_issue_9214 ok
test_issue_11617 ok
test_transform ok
test_concyclic_doctest_bug ok
test_arguments ok
test_unit ok
test_dot ok
test__normalize_dimension ok
test_direction_cosine ok                                                    [OK]


================== tests finished: 12 passed, in 8.68 seconds ==================
```

### Classification
✅ All 2 FAIL_TO_PASS tests now pass
✅ Zero regressions in 9 PASS_TO_PASS tests
✅ No pre-existing failures affecting the verdict

The `__rmul__` implementation successfully enables left multiplication for Point objects, resolving both test_point and test_point3D failures without introducing any regressions.
