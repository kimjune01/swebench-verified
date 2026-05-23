# Hypothesis graph: sympy__sympy-15017

---

## H₀: _loop_size computed incorrectly for rank-0 arrays (ACTIVE)
**Mode**: deduction  
**Confidence**: 99%  
**Status**: proposed for /craft

### Observation
Test `test_ndim_array_initiation` fails with:
```
AssertionError at line 80: assert len(rank_zero_array) == 1
```

Rank-0 array created with `ImmutableDenseNDimArray(x)`:
- Expected: `len() == 1`, `shape == ()`, `rank == 0`
- Actual: `len() == 0` (WRONG)

### Root cause
All four array implementations compute `_loop_size` (returned by `__len__`) as:
```python
self._loop_size = functools.reduce(lambda x,y: x*y, shape) if shape else 0
```

For rank-0 arrays where `shape = ()`:
- Empty tuple is falsy → `if shape` is False → returns 0
- But mathematically correct product of empty sequence is 1 (multiplicative identity)

### Evidence
- `ndim_array.py:178`: `def __len__(self): return self._loop_size`
- `ndim_array.py:69`: `if index >= self._loop_size: raise ValueError("index out of range")`
- `dense_ndim_array.py:152,177`: Two instances of the buggy formula
- `sparse_ndim_array.py:~135,170`: Two more instances
- REPL verification: `functools.reduce(lambda x,y: x*y, (), 1)` → 1 ✓

### Fix specification
Change all four locations from:
```python
functools.reduce(lambda x,y: x*y, shape) if shape else 0
```
to:
```python
functools.reduce(lambda x,y: x*y, shape, 1)
```

This correctly handles:
- `shape = ()` → 1 (rank-0 scalar)
- `shape = (0,)` → 0 (rank-1 empty array)
- `shape = (3,4)` → 12 (rank-2 array)

### Edit sites
1. `sympy/tensor/array/dense_ndim_array.py:152` (ImmutableDenseNDimArray._new)
2. `sympy/tensor/array/dense_ndim_array.py:177` (MutableDenseNDimArray._new)
3. `sympy/tensor/array/sparse_ndim_array.py:~135` (ImmutableSparseNDimArray.__new__)
4. `sympy/tensor/array/sparse_ndim_array.py:170` (MutableSparseNDimArray.__new__)

## Craft Gate Loop

### Iteration 1: Draft & Volley

**Initial diagnosis from recon:** Fix `_loop_size` computation by changing `functools.reduce(lambda x,y: x*y, shape) if shape else 0` to use initial value 1.

**Drafted diff:** Change all 4 locations to `functools.reduce(lambda x,y: x*y, shape, 1)`

**Codex feedback:** Proposed fix is too broad. The issue is that:
- `shape=(0,)` should still have `loop_size=0` (product is 0)
- `shape=()` (rank-0) should have `loop_size=len(flat_list)`
- The correct fix is `if shape else len(flat_list)` not `if shape else 1`

This preserves:
- `shape=(0,)` → 0
- `shape=()` with one scalar → 1  
- `shape=()` with no elements → 0

**Revised fix:** Applied `functools.reduce(lambda x,y: x*y, shape) if shape else len(flat_list)` to all 4 locations:
- sympy/tensor/array/dense_ndim_array.py:152 (ImmutableDenseNDimArray)
- sympy/tensor/array/dense_ndim_array.py:177 (MutableDenseNDimArray)
- sympy/tensor/array/sparse_ndim_array.py:133 (ImmutableSparseNDimArray)
- sympy/tensor/array/sparse_ndim_array.py:170 (MutableSparseNDimArray)

### Gate Result: PASS

All 16 tests in test_immutable_ndim_array.py passed, including `test_ndim_array_initiation`.

**Resolution:** The fix correctly handles rank-0 arrays by falling back to `len(flat_list)` when shape is empty.

---

## Audit: sympy__sympy-15017

### FAIL_TO_PASS
- test_ndim_array_initiation: ✅ PASS (was failing with `assert len(rank_zero_array) == 1` AssertionError on base)

### PASS_TO_PASS regressions
None. All 14 PASS_TO_PASS tests continue to pass:
- test_reshape: ok
- test_iterator: ok
- test_sparse: ok
- test_calculation: ok
- test_ndim_array_converting: ok
- test_converting_functions: ok
- test_equality: ok
- test_arithmetic: ok
- test_higher_dimenions: ok
- test_rebuild_immutable_arrays: ok
- test_slices: ok
- test_diff_and_applyfunc: ok
- test_op_priority: ok
- test_symbolic_indexing: ok

### Pre-existing failures (not counted)
None.

### Gate output
```
============================= test process starts ==============================
sympy/tensor/array/tests/test_immutable_ndim_array.py[16] 
test_ndim_array_initiation ok
[... all 16 tests ok ...]
================== tests finished: 16 passed, in 0.04 seconds ==================
```

### Analysis
The fix changed `_loop_size` computation from `if shape else 0` to `if shape else len(flat_list)` in all four array implementations (ImmutableDense, MutableDense, ImmutableSparse, MutableSparse). This correctly handles rank-0 arrays (empty shape tuple) by returning the length of the actual data, while preserving correct behavior for rank-1+ arrays including zero-element arrays like `shape=(0,)`.

All FAIL_TO_PASS tests now pass. Zero regressions in PASS_TO_PASS tests. Clean resolution.
