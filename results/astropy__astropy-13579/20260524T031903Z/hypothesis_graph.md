# Hypothesis graph: astropy__astropy-13579

## H₀ (abduction, 2026-05-23)
**Symptom:** `test_coupled_world_slicing` fails because `SlicedLowLevelWCS.world_to_pixel_values()` returns `1.81818182e+11` for the first pixel coordinate instead of `0`.

**Observation:** The test creates a 3D WCS with PC matrix that couples spatial and spectral dimensions (PC1_2=-1.0, PC2_3=-1.0). When slicing at wavelength index 0 and calling `world_to_pixel_values` with the first two world coordinates, the result is wrong.

**Evidence:**
- Full WCS with correct 3rd world coord (1.05e-10): returns pixel (≈0, ≈0, 0) ✓
- Full WCS with placeholder 1.0 as 3rd coord: returns pixel (1.81e11, ≈0, 1.81e11) ✗
- Sliced WCS (buggy): returns pixel (1.81e11, ≈0) ✗

## H₁ (deduction, 95%)
**Root cause:** In `astropy/wcs/wcsapi/wrappers/sliced_wcs.py:254`, `world_to_pixel_values` uses hardcoded `1.` as placeholder for dropped world dimensions instead of the actual world coordinate value at the sliced position.

**Supporting evidence:**
- `sliced_wcs.py:254` — `world_arrays_new.append(1.)` — fills dropped dimensions with constant
- `sliced_wcs.py:175` — `dropped_info["value"].append(world_coords[i])` — actual values ARE computed and stored in `dropped_world_dimensions`
- Axis correlation matrix shows all world dims couple to all pixel dims in this test case
- When dimensions are coupled, incorrect world values propagate through the PC matrix transformation

**Fix specification:**
Replace line 254's `world_arrays_new.append(1.)` with `world_arrays_new.append(self.dropped_world_dimensions["value"][iworld_dropped])`, tracking dropped dimension index similarly to how kept dimensions are tracked.

**Confidence:** 95% (deduction) — traced the data flow, reproduced the exact error value by manually passing 1.0 instead of correct world coord.

## Craft: Gate Loop

### Iteration 1: Initial fix

**Approach:** Following recon diagnosis, replaced hardcoded `1.` placeholder with actual world coordinate values from sliced position. Used `_pixel_to_world_values_all(*[0] * len(self._pixel_keep))` to compute the correct world coordinates for dropped dimensions, then indexed with `iworld` to get the value for each sliced dimension.

**Codex review:** Confirmed this is the cleaner approach (vs. using `dropped_world_dimensions["value"]`). Using direct computation avoids repeated property access and maintains consistent indexing.

**Changes:**
- `astropy/wcs/wcsapi/wrappers/sliced_wcs.py:245-258`: Added `sliced_out_world_coords` computation at start of `world_to_pixel_values` method
- Replaced `world_arrays_new.append(1.)` with `world_arrays_new.append(sliced_out_world_coords[iworld])`

**Gate result:** ✅ GREEN - All 41 tests passed, including target test `test_coupled_world_slicing`

**Resolution:** FAIL_TO_PASS test now passes. The fix correctly uses actual world coordinate values instead of hardcoded placeholders when dimensions are coupled via PC matrix.

## Audit: astropy__astropy-13579

**Patch verified:** 5 insertions, 1 deletion in `astropy/wcs/wcsapi/wrappers/sliced_wcs.py`

### FAIL_TO_PASS
- `test_coupled_world_slicing`: **PASS** ✓

### PASS_TO_PASS regressions
**None** — all 40 baseline-passing tests still pass.

### Pre-existing failures (not counted)
**None** — the baseline capture showed only `test_coupled_world_slicing` failing, which now passes.

### Gate result
All 41 tests PASSED. The fix correctly computes world coordinates for sliced-out dimensions instead of using hardcoded `1.`, which resolves the coupling issue when dimensions are correlated via the PC matrix.

**VERDICT:** RESOLVED
**RE-ENTER:** none
