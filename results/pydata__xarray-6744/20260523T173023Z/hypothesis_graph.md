# Hypothesis graph: pydata__xarray-6744

## H₁: Iterator ignores center parameter (Abduction - 85%)

**Failure mode:** The `__iter__` method in `DataArrayRolling` always computes left-aligned windows, ignoring the `self.center` parameter.

**Evidence:**
- File: `xarray/core/rolling.py:270-283`
- The `__iter__` method computes windows using:
  ```python
  stops = np.arange(1, len(self.window_labels) + 1)
  starts = stops - int(self.window[0])
  starts[: int(self.window[0])] = 0
  ```
- This produces left-aligned windows regardless of `self.center[0]` value
- No conditional logic checks `self.center` in `__iter__`

**Test verification:**
- With center=True, window=3, data=[0,1,2,3,4]:
  - Expected from `.mean()`: [nan, 1., 2., 3., nan]  
  - Actual from iteration: [nan, nan, 1., 2., 3.]
  - Windows are offset by 1 position (left-aligned instead of centered)

**Root cause:** 
Lines 273-275 in `xarray/core/rolling.py` compute window indices without checking `self.center[0]`.

**Fix required:**
When `self.center[0]` is True, adjust window calculation to center windows:
```python
offset = self.window[0] // 2
starts = np.arange(len(self.window_labels)) - offset
stops = starts + self.window[0]
starts = np.maximum(starts, 0)  # clip negative indices
```

**Confidence:** Abduction - 85% (directly traced code path, verified with test data)


## Craft: Gate Loop

### Iteration 1: Applied centered window fix

**Hypothesis**: The `__iter__` method ignores `self.center[0]` and always produces left-aligned windows. When `center=True`, windows should be centered at position i using offset = window // 2.

**Edit applied**: Modified `xarray/core/rolling.py` lines 270-283 to add conditional logic:
- When `self.center[0]` is True: compute centered windows with `offset = window // 2`, `starts = indices - offset`, `stops = indices + (window - offset)`
- When `self.center[0]` is False: preserve existing left-aligned logic

**Gate result**: ✅ **PASS** — All 1818 tests passed (32 skipped, 4 xpassed, 0 failed)

**FAIL_TO_PASS resolution**:
- ✅ `test_rolling_iter[numpy-3-True-1]` — PASS
- ✅ `test_rolling_iter[numpy-3-True-2]` — PASS  
- ✅ `test_rolling_iter[numpy-7-True-1]` — PASS

**Status**: RESOLVED — The centered window logic now matches the behavior of rolling reduction methods.

## Audit: pydata__xarray-6744

### Phase 1: Patch confirmation
```
 xarray/core/rolling.py | 13 ++++++++++---
 1 file changed, 10 insertions(+), 3 deletions(-)
```
✅ Patch is live in the tree.

### Phase 2: Gate execution
Full gate: 1818 passed, 32 skipped, 4 xpassed, 0 failed (41.46s)

### Phase 3: Result classification

#### FAIL_TO_PASS
- ✅ xarray/tests/test_rolling.py::TestDataArrayRolling::test_rolling_iter[numpy-3-True-1]: PASS
- ✅ xarray/tests/test_rolling.py::TestDataArrayRolling::test_rolling_iter[numpy-3-True-2]: PASS
- ✅ xarray/tests/test_rolling.py::TestDataArrayRolling::test_rolling_iter[numpy-7-True-1]: PASS

#### PASS_TO_PASS regressions
None — all tests passed.

#### Pre-existing failures (not counted)
None identified — the 32 skipped tests and 4 xpassed tests are expected per the fail-on-base capture.

### Phase 4: Verdict
All FAIL_TO_PASS tests now pass, and zero PASS_TO_PASS regressions were introduced. The fix correctly handles centered windows in the `__iter__` method by adding conditional logic that computes window offsets based on `self.center[0]`.

VERDICT: RESOLVED
RE-ENTER: none
