# Hypothesis graph: astropy__astropy-13977

## H0: Initial Diagnosis (abduction)
**Date**: 2026-05-23
**Mode**: Abduction (~75% confidence)

**Symptom**: Tests fail with `ValueError: Value not scalar compatible or convertible to an int, float, or complex array` when calling ufuncs like `np.add(quantity, duck_quantity)` where `duck_quantity` is a duck-typed Quantity that implements `__array_ufunc__`.

**Root Cause**: 
`Quantity.__array_ufunc__()` raises `ValueError` when it encounters incompatible duck-typed inputs instead of returning `NotImplemented`. The error occurs in this chain:
1. `Quantity.__array_ufunc__` (quantity.py:644) calls `converters_and_unit()` to get unit converters
2. For compatible units (e.g., m and mm), it creates a converter lambda at core.py:1073: `lambda val: scale * _condition_arg(val)`
3. When applying this converter to a duck-typed input at quantity.py:670, `_condition_arg()` is called with the duck object
4. `_condition_arg()` (core.py:2629) raises `ValueError` because it doesn't recognize the duck type
5. This ValueError propagates up instead of allowing `__array_ufunc__` to return `NotImplemented`

According to NumPy's `__array_ufunc__` protocol and the issue description, when a ufunc encounters incompatible types, it should return `NotImplemented` to allow reflected operations. The existing code in `Quantity.__eq__` already follows this pattern (catching exceptions and returning `NotImplemented`).

**Evidence**:
- `astropy/units/quantity.py:670` - converter application: `arrays.append(converter(input_) if converter else input_)`
- `astropy/units/core.py:1073` - converter creation: `return lambda val: scale * _condition_arg(val)`
- `astropy/units/core.py:2629` - raises ValueError: `raise ValueError("Value not scalar compatible...")`
- `astropy/units/quantity.py:~1520` - `__eq__` uses try/except pattern returning `NotImplemented`

**Edit Sites**:
1. `astropy/units/quantity.py` lines 644-671 (inside `__array_ufunc__` method):
   - Wrap `converters_and_unit()` call and converter application in try-except
   - Catch `TypeError` and `ValueError` (and potentially `UnitConversionError` from incompatible types)
   - Return `NotImplemented` instead of letting exceptions propagate
   - This allows duck-typed inputs with their own `__array_ufunc__` to handle the operation

**Alternative**: Could also modify `_condition_arg` or the converter lambda to return a sentinel value instead of raising, but that would require more invasive changes across the codebase.


## Craft Gate Loop

### Attempt 1 - Partial fix (converter application only)
**Hypothesis**: Wrapping only the converter application loop with try-except would handle duck arrays.

**Change**: Added try-except around lines 668-671 (converter application), catching TypeError/ValueError (except UnitConversionError), returning NotImplemented when duck arrays detected.

**Gate result**: Divergent (progress) - 40/48 tests passed. Tests with `out=None` passed, but tests with `out="empty"` (duck-array outputs) failed with `UnitTypeError` from `check_output()`.

**E-value**: The fix addressed converter application but missed `check_output()` and `converters_and_unit()` call sites.

### Attempt 2 - Complete fix (all three call sites)
**Hypothesis**: Need to wrap all three error-prone call sites: `converters_and_unit()`, `check_output()`, and converter application.

**Changes applied**:
1. Wrapped `converters_and_unit()` call (line 644) - catch TypeError, check for duck arrays, return NotImplemented
2. Wrapped `check_output()` call (line 653) - catch TypeError/UnitTypeError, check for duck arrays in both inputs and outputs, return NotImplemented  
3. Wrapped converter application loop (line 668) - catch TypeError/ValueError (except UnitConversionError), check for duck arrays, return NotImplemented

Duck array detection: `hasattr(obj, "__array_ufunc__") and obj.__array_ufunc__ is not None and not isinstance(obj, Quantity)`

**Gate result**: ✅ **GREEN** - All 342 tests passed, 4 skipped, 1 xfailed

**Verification**: All FAIL_TO_PASS tests now pass:
- Binary ufuncs (np.add, np.less) with duck quantities work
- Both `out=None` and `out=duck_quantity` cases work  
- UnitConversionError still raised for incompatible Quantity units (as intended)

**Resolution**: The fix correctly implements NumPy's `__array_ufunc__` protocol by returning `NotImplemented` when encountering duck-array types that Quantity cannot handle, allowing those types to process the operation instead.

## Audit: astropy__astropy-13977
**Date**: 2026-05-23
**Auditor**: Claude Code /audit

### Phase 1: Patch Verification
✅ Patch live in tree: `astropy/units/quantity.py | 35 insertions(+), 5 deletions(-)`

### Phase 2: Gate Execution
Gate output: **342 passed, 4 skipped, 1 xfailed** in 0.38s

### Phase 3: Classification

#### FAIL_TO_PASS Tests (20 tests - ALL NOW PASSING ✅)
All tests from `TestUfuncReturnsNotImplemented::TestBinaryUfuncs::test_full` with duck-typed quantities:

**out=None tests (8 tests)** - all PASSED:
- test_full[None-duck_quantity0-quantity0-add] - PASSED
- test_full[None-duck_quantity0-quantity0-less] - PASSED
- test_full[None-duck_quantity0-quantity1-add] - PASSED
- test_full[None-duck_quantity0-quantity1-less] - PASSED
- test_full[None-duck_quantity1-quantity0-add] - PASSED
- test_full[None-duck_quantity1-quantity0-less] - PASSED
- test_full[None-duck_quantity1-quantity1-add] - PASSED
- test_full[None-duck_quantity1-quantity1-less] - PASSED

**out=empty tests (12 tests)** - all PASSED:
- test_full[empty-duck_quantity0-quantity0-add] - PASSED
- test_full[empty-duck_quantity0-quantity0-multiply] - PASSED
- test_full[empty-duck_quantity0-quantity0-less] - PASSED
- test_full[empty-duck_quantity0-quantity1-add] - PASSED
- test_full[empty-duck_quantity0-quantity1-multiply] - PASSED
- test_full[empty-duck_quantity0-quantity1-less] - PASSED
- test_full[empty-duck_quantity1-quantity0-add] - PASSED
- test_full[empty-duck_quantity1-quantity0-multiply] - PASSED
- test_full[empty-duck_quantity1-quantity0-less] - PASSED
- test_full[empty-duck_quantity1-quantity1-add] - PASSED
- test_full[empty-duck_quantity1-quantity1-multiply] - PASSED
- test_full[empty-duck_quantity1-quantity1-less] - PASSED

#### PASS_TO_PASS Regressions
**None** - Zero failures in gate output.

#### Pre-existing Failures
**None** - The 4 skipped and 1 xfailed match baseline behavior.

### Phase 4: Verdict

**Contract fulfilled**:
- ✅ All 20 FAIL_TO_PASS tests now PASS
- ✅ Zero PASS_TO_PASS regressions
- ✅ Full test suite green (342/342 passed)

The patch successfully implements NumPy's `__array_ufunc__` protocol by wrapping three critical call sites (converters_and_unit, check_output, and converter application) with try-except blocks that return `NotImplemented` when encountering duck-typed arrays, allowing proper delegation to the duck array's own `__array_ufunc__` implementation.

