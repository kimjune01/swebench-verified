# Hypothesis graph: sympy__sympy-16792

## Hypothesis H₀ (abduction, 85%)
**Status**: Initial diagnosis
**Timestamp**: Phase 1 recon

The test `test_ccode_unused_array_arg` fails because when a MatrixSymbol is passed in `argument_sequence` but does not appear in the expression being code-generated, the resulting `InputArgument` is created without dimension metadata. This causes the C code generator to emit `double x` instead of `double *x` in the function signature.

**Root cause**: In `sympy/utilities/codegen.py:741`, when processing `argument_sequence`, if a symbol is not found in `name_arg_dict` (meaning it wasn't in the expression), a new `InputArgument(symbol)` is created without checking if the symbol is a MatrixSymbol or IndexedBase that requires dimension metadata.

**Evidence**:
- Line 701-704: `array_symbols` is built only from symbols in the expression
- Line 706-713: Dimensions are set for symbols in `array_symbols`
- Line 739-741: When a symbol from `argument_sequence` is not found, `InputArgument(symbol)` is created without dimensions
- Confirmed: `InputArgument` for `x` has `dimensions=None` when `x` doesn't appear in expression

**Fix**: In the `except KeyError:` block at line 741, check if `symbol` is a `MatrixSymbol` or `IndexedBase` and create dimensions metadata similar to lines 707-713.

## Gate iteration 1 (convergent, PASS)
**Timestamp**: 2026-05-23T11:18:00
**Action**: Applied minimal fix for MatrixSymbol at line 742

**Codex feedback (iteration 0)**: 
- Identified that `IndexedBase` is normalized to `.label` earlier in the code (lines 724-729)
- By the time we reach the KeyError block, IndexedBase is already a Symbol
- The fix should focus on MatrixSymbol only, which is what the failing test requires
- Warned about `shape=None` edge cases, but not applicable to MatrixSymbol

**Patch applied**:
```python
# sympy/utilities/codegen.py lines 742-746
except KeyError:
    if isinstance(symbol, MatrixSymbol):
        dims = [(S.Zero, dim - 1) for dim in symbol.shape]
        new_args.append(InputArgument(symbol, dimensions=dims))
    else:
        new_args.append(InputArgument(symbol))
```

**Gate result**: ✅ ALL TESTS PASS (56 passed in 1.01s)
- `test_ccode_unused_array_arg` now passes
- No regressions in other tests

**Trajectory**: Convergent success - first iteration resolves the issue completely.

**Resolution**: The diagnosis was accurate. MatrixSymbol instances in `argument_sequence` that don't appear in the expression now correctly receive dimension metadata, causing the C code generator to emit pointer parameters instead of scalar parameters.

## Audit: sympy__sympy-16792
**Timestamp**: 2026-05-23 (final verification)

### FAIL_TO_PASS
- `test_ccode_unused_array_arg`: **PASS** ✓

### PASS_TO_PASS regressions
None — all 55 PASS_TO_PASS tests remain passing.

### Pre-existing failures (not counted)
None.

### Gate output
```
================== tests finished: 56 passed, in 1.01 seconds ==================
```

All tests pass. The craft patch successfully resolved the issue:
- The target test `test_ccode_unused_array_arg` now passes (was failing on base)
- Zero regressions introduced
- All 55 PASS_TO_PASS tests continue to pass

**VERDICT**: RESOLVED
**RE-ENTER**: none
