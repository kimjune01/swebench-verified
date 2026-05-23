# Hypothesis graph: pydata__xarray-6938

## H₀: to_index_variable() returns self instead of copy (abduction)

**Status**: Root cause identified  
**Confidence**: 95% (deduction - traced through code)

### Failure symptom
Test `test_to_index_variable_copy` fails because:
```python
a = IndexVariable("x", ["a"])
b = a.to_index_variable()
assert a is not b  # FAILS - a and b are the same object
```

### Root cause
`IndexVariable.to_index_variable()` at line 2883 of `xarray/core/variable.py` returns `self` instead of returning a copy:

```python
def to_index_variable(self):
    """Return this variable as an xarray.IndexVariable"""
    return self  # ← Returns same object, not a copy
```

This contrasts with `Variable.to_index_variable()` at line 549, which creates a NEW IndexVariable:

```python
def to_index_variable(self):
    """Return this variable as an xarray.IndexVariable"""
    return IndexVariable(
        self.dims, self._data, self._attrs, encoding=self._encoding, fastpath=True
    )  # ← Creates a new object
```

### Why this causes swap_dims to mutate
In `Dataset.swap_dims()` at lines 3774-3776 of `xarray/core/dataset.py`:

```python
if k in result_dims:
    var = v.to_index_variable()  # If v is IndexVariable, returns v itself
    var.dims = dims  # Mutates the original variable's dims!
```

When `v` is already an IndexVariable:
1. `to_index_variable()` returns `v` (same object)
2. `var.dims = dims` modifies `v.dims` (same object)
3. Original variable in dataset is mutated

### Historical context
Git commit 3ecfa666 (2016) shows `return self` was intentional - likely for efficiency since IndexVariable is already the correct type. However, this breaks the expected contract that `to_index_variable()` returns an independent object that can be modified.

### Edit site
**File**: `xarray/core/variable.py`  
**Lines**: 2882-2884  
**Change**: Replace `return self` with `return self.copy(deep=False)` to return a shallow copy


## Craft gate loop — pydata__xarray-6938

### Iteration 1: Initial fix

**Hypothesis**: `IndexVariable.to_index_variable()` returns `self` instead of a copy, causing mutations to affect the original object.

**Edit applied**: Changed line 2884 in `xarray/core/variable.py` from `return self` to `return self.copy(deep=False)`.

**Codex review**: Approved. "Patch is minimal and right." Noted that the shallow copy avoids expensive data copies since the pandas index backing data is effectively immutable.

**Gate result**: ✅ PASSED
- Target test `xarray/tests/test_variable.py::TestIndexVariable::test_to_index_variable_copy` now passes
- All 431 tests passed, 58 skipped, 15 xfailed, 23 xpassed
- No regressions detected

**Trajectory**: Convergent success — the fix directly resolved the root cause on first attempt.

**Resolution**: RESOLVED. The working tree contains the minimal fix that makes FAIL_TO_PASS pass without breaking existing tests.


## Audit: pydata__xarray-6938

**Patch confirmed live**: 1 file changed, 1 insertion(+), 1 deletion(-)

```diff
diff --git a/xarray/core/variable.py b/xarray/core/variable.py
index 5827b90a..d03654e9 100644
--- a/xarray/core/variable.py
+++ b/xarray/core/variable.py
@@ -2881,7 +2881,7 @@ class IndexVariable(Variable):
 
     def to_index_variable(self):
         """Return this variable as an xarray.IndexVariable"""
-        return self
+        return self.copy(deep=False)
```

### FAIL_TO_PASS
- `xarray/tests/test_variable.py::TestIndexVariable::test_to_index_variable_copy`: **PASSED** ✓

### PASS_TO_PASS regressions
None. All 431 tests passed.

### Pre-existing (not counted)
None. All xfail/xpass are expected test states, not failures.

### Gate summary
- 431 passed
- 58 skipped
- 15 xfailed (expected)
- 23 xpassed (bonus passes)
- 0 failures
- 0 regressions

**Contract fulfilled**: All FAIL_TO_PASS tests pass AND zero PASS_TO_PASS regressions.

VERDICT: RESOLVED  
RE-ENTER: none
