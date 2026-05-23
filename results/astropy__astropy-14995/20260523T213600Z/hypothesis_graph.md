# Hypothesis graph: astropy__astropy-14995

## H₀: Initial Hypothesis (Abduction)

**Timestamp**: Initial recon pass  
**Node Type**: Abduction  
**Confidence**: 95% (deduction from code trace)

The tests fail because `_arithmetic_mask` method in `astropy/nddata/mixins/ndarithmetic.py` does not handle the case where `operand is not None` but `operand.mask is None`. When this occurs, the code falls through to line 527 which calls `handle_mask(self.mask, operand.mask, **kwds)` with `operand.mask=None`, causing a TypeError when `handle_mask` is `np.bitwise_or`.

**Root Cause**: Incomplete logic flow in `_arithmetic_mask` method at lines 516-527. The method checks:
1. If both masks are None or handle_mask is None → return None
2. If self.mask is None and operand exists → return operand.mask  
3. If operand is None → return self.mask
4. Else → call handle_mask on both masks

The missing case is: `self.mask is not None` AND `operand is not None` AND `operand.mask is None`.

**Introduced by**: Commit `feeb716b74` (Brett M. Morris, 2022-12-13) changed line 523 from:
```python
elif operand.mask is None:
```
to:
```python
elif operand is None:
```

This was meant to support collapse operations where operand is None, but it inadvertently removed the check for when operand exists but has no mask.

**Edit Site**: `astropy/nddata/mixins/ndarithmetic.py` lines 516-527

**Fix**: Add explicit check for `operand.mask is None` before the final else clause:
```python
elif operand.mask is None:
    return deepcopy(self.mask)
```

This should be inserted between line 524 and line 525.

## Craft iteration 1 (gate: PASS)

**Fix applied**: Modified `astropy/nddata/mixins/ndarithmetic.py` line 523 to handle both `operand is None` and `operand.mask is None` cases:

```python
elif operand is None or operand.mask is None:
    return deepcopy(self.mask)
```

**codex pre-gate review**: "No bug in the proposed logic. It restores the missing 'left mask only' case and avoids calling `handle_mask(self.mask, None, **kwds)` which breaks with `np.bitwise_or`. The patch is narrowly correct."

**Gate result**: ✅ PASSED — All 180 tests passed, including `test_nddata_bitmask_arithmetic`.

**Trajectory**: Convergent (resolved) — First iteration success.

## Audit: astropy__astropy-14995

**Timestamp**: 2026-05-23  
**Gate**: Full test suite (`pytest -rA astropy/nddata/mixins/tests/test_ndarithmetic.py`)

### Patch verification
```
astropy/nddata/mixins/ndarithmetic.py | 2 +-
1 file changed, 1 insertion(+), 1 deletion(-)
```
Patch is live. Changed line 523 from `elif operand is None:` to `elif operand is None or operand.mask is None:`.

### FAIL_TO_PASS
- `astropy/nddata/mixins/tests/test_ndarithmetic.py::test_nddata_bitmask_arithmetic`: **PASS** ✅

### PASS_TO_PASS regressions
None. All 180 tests passed.

### Pre-existing failures (not counted)
None. Baseline capture showed all tests passing before the fix (except the FAIL_TO_PASS test which was not present in the baseline output).

### Classification
- All FAIL_TO_PASS tests pass: ✅
- Zero PASS_TO_PASS regressions: ✅
- Full contract satisfied: **RESOLVED**

The fix correctly handles the case where `operand is not None` but `operand.mask is None`, preventing the TypeError that occurred when `handle_mask(self.mask, None, **kwds)` was called with `np.bitwise_or` as the handler.

