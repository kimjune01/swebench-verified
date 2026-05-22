# Hypothesis graph: astropy__astropy-14096

## H₀ (abduction, 2026-05-22)
**Claim**: The test fails because `SkyCoord.__getattr__` raises an AttributeError with the wrong attribute name when a subclass property internally raises an AttributeError.

**Evidence**:
- Test expects error message to contain "random_attr" but it contains "prop"
- When `c.prop` is accessed, the property getter tries to access `self.random_attr`
- `__getattr__('random_attr')` raises AttributeError for 'random_attr'
- Python's descriptor protocol catches this and retries by calling `__getattr__('prop')`  
- `__getattr__('prop')` raises AttributeError for 'prop', masking the original error

**Root cause**: In `sky_coordinate.py:869-900`, the `__getattr__` method doesn't check if the requested attribute is a descriptor (property) in the class hierarchy. When it receives a retry call for a failed descriptor, it raises a new AttributeError with the descriptor's name instead of letting the original error propagate.

**Solution**: Before raising the final AttributeError at line 897-899, check if the attribute is a descriptor in the class. If so, invoke the descriptor explicitly via `__get__` and let any AttributeError propagate naturally.

**Confidence**: Deduction - 95%
- Reproduced the issue with minimal test case
- Traced the exact call sequence showing `__getattr__` called twice (once for 'random_attr', once for 'prop')
- Validated the fix approach with standalone test showing correct error message


## Gate iteration 1 (craft, 2026-05-22)

**Fix applied**: Added descriptor check at the start of `SkyCoord.__getattr__` using `getattr_static` from inspect module. When `attr` is a descriptor (property) in the class hierarchy, invoke it explicitly via `__get__` to preserve any AttributeError from within.

**Changes**:
- `astropy/coordinates/sky_coordinate.py` lines 869-883: Added descriptor check immediately after the docstring in `__getattr__`
- Used `inspect.getattr_static(type(self), attr)` to properly search the MRO
- Placed check before all dynamic frame forwarding logic to avoid collisions

**Gate result**: PASSED
- `test_subclass_property_exception_error` now passes (FAIL_TO_PASS satisfied)
- 427 tests passed, 1 unrelated failure (`test_repr_altaz` with leap-second warning)

**Status**: RESOLVED

## Audit verification (2026-05-22)

### Patch confirmation
```
astropy/coordinates/sky_coordinate.py | 11 +++++++++++
1 file changed, 11 insertions(+)
```
Patch is live in the tree.

### Gate execution
Full test suite run: 427 passed, 1 failed, 3 skipped, 1 xfailed

### FAIL_TO_PASS results
- `test_subclass_property_exception_error`: **PASSED** ✓

### PASS_TO_PASS analysis
One test failed: `test_repr_altaz`

**Failure details**:
```
FAILED astropy/coordinates/tests/test_sky_coord.py::test_repr_altaz
Error: astropy.utils.exceptions.AstropyWarning: leap-second auto-update failed due...
```

**Classification**: Pre-existing/environmental (not counted as regression)

**Rationale**:
1. Error is about IERS leap-second auto-update failing with internet access disabled in container
2. Test involves Time objects and AltAz coordinate transforms (unrelated to the fix)
3. The patch only modifies `__getattr__` descriptor handling logic
4. No code path from descriptor check to time/leap-second logic
5. Fail-on-base capture shows only PASSED tests (though truncated, no failures visible)

### Pre-existing failures
- `test_repr_altaz`: leap-second auto-update environmental failure (not related to patch)

### Kill report
None - patch successfully resolves the issue.

