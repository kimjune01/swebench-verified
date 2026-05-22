# Hypothesis graph: mwaskom__seaborn-3069

## Recon Round 1 - Initial Diagnosis

### H₀: Test failure cause (abduction)
The tests fail because nominal scales do not apply the special categorical axis tweaks (limits, grid hiding, y-inversion) that categorical plots use.

**Evidence:**
- `test_nominal_x_axis_tweaks`: expects xlim=(-0.5, 2.5) but gets (-0.055, 0.055)
- `test_nominal_y_axis_tweaks`: expects ylim=(2.5, -0.5) but gets (-0.055, 0.055)  
- Both have visible gridlines when they should be hidden

### Root Cause Hypothesis (deduction, 95%)

**File:** `seaborn/_core/plot.py`
**Method:** `Plotter._finalize_figure` (line 1628)

The method only handles explicit user-provided limits from `p._limits`. When no explicit limits are set, matplotlib's default auto-scaling applies, which:
1. Uses ~5% margins instead of the required +/- 0.5 padding
2. Doesn't invert the y-axis for nominal scales
3. Doesn't turn off gridlines

**Supporting evidence:**
- Line 1636: `if axis_key in p._limits:` - only processes when explicit limits exist
- Lines 1641-1644: Has logic for string limits (+/- 0.5) but only within the explicit limits block
- No code checks if a scale is `Nominal` and applies categorical axis behavior automatically

**What needs to change:**
After the explicit limits block, add logic to:
1. Check if `self._scales[axis_key]` is a `Nominal` instance
2. If yes and no explicit limit was set:
   - Get number of categories from `ax.{axis}axis.units._mapping`
   - Set limits to `(-0.5, n-0.5)` for x-axis or `(n-0.5, -0.5)` for y-axis
   - Call `ax.{axis}axis.grid(False)` to hide gridlines


## Craft Gate Loop

### Iteration 1: Draft and codex volley

**Hypothesis**: Add elif block after explicit limits handling to check for Nominal scale and apply categorical defaults.

**Draft approach**:
1. Import `Nominal` at module level
2. Add `elif` after explicit limits block to check if scale is Nominal
3. Get number of categories from axis units mapping
4. Set limits to (-0.5, n-0.5) for x, (n-0.5, -0.5) for y
5. Disable gridlines

**Codex feedback (iteration 1)**:
- Indentation wrong - `elif` was inside the `if` block instead of aligned with it
- Relies on private `._mapping` attribute - brittle
- Grid disabling coupled to mapping check
- Doesn't handle edge cases (empty nominal, inverted axes)

**Revised approach (iteration 2)**:
- Fixed indentation to align `elif` with `if`
- Use `get_view_interval()` instead of private `._mapping`

**Codex feedback (iteration 2)**:
- `get_view_interval()` is mutable state, not category metadata - fragile
- For inverted y-axis, deriving `n = int(vmax) + 1` breaks
- `elif` structure skips grid disabling when explicit limits are set
- Should use `which="both"` for grid disabling
- Should use `auto=None` when setting limits

**Final approach (codex-recommended)**:
```python
if isinstance(self._scales.get(axis_key), Nominal):
    axis_obj.grid(False, which="both")
    if axis_key not in p._limits:
        nticks = len(axis_obj.get_major_ticks())
        lo, hi = -.5, nticks - .5
        if axis == "y":
            lo, hi = hi, lo
        getattr(ax, f"set_{axis}lim")(lo, hi, auto=None)
```

**Key improvements**:
- Unconditionally disable grid for nominal axes (even with explicit limits)
- Use `len(axis_obj.get_major_ticks())` to get category count
- Cleaner control flow with nested if
- Use `auto=None` to preserve autoscale state

**Applied**: seaborn/_core/plot.py lines 28 (import) and 1647-1656 (nominal handling)

### Gate result (iteration 1): PASS

```
tests/_core/test_plot.py::TestScaling::test_nominal_x_axis_tweaks PASSED
tests/_core/test_plot.py::TestScaling::test_nominal_y_axis_tweaks PASSED
```

**Evidence trajectory**: Convergent success - both FAIL_TO_PASS tests pass on first gate attempt.

**E-value**: Deduction - high confidence. The fix:
1. Imports Nominal at module level for type checking
2. Detects nominal scales in _finalize_figure
3. Disables gridlines for all nominal axes
4. Sets categorical-specific limits (-0.5, n-0.5) only when no explicit limit provided
5. Inverts y-axis limits for nominal scales as expected


## Audit: mwaskom__seaborn-3069

### Patch verification

**Patch status:** Live in tree
```
seaborn/_core/plot.py | 13 ++++++++++++-
1 file changed, 12 insertions(+), 1 deletion(-)
```

### Gate results (with patch)

**Summary:** 96 passed, 74 failed, 5 xfailed

### FAIL_TO_PASS

✅ tests/_core/test_plot.py::TestScaling::test_nominal_x_axis_tweaks - PASS
✅ tests/_core/test_plot.py::TestScaling::test_nominal_y_axis_tweaks - PASS

Both target tests now pass.

### PASS_TO_PASS regressions

**None.** All current failures are pre-existing.

### Pre-existing failures (not counted, confirmed against base capture)

All 74 current failures existed on base (76 total base failures minus 2 fixed FAIL_TO_PASS tests):

**TestLayerAddition (10 failures):**
- test_without_data, test_with_new_variable_by_name, test_with_new_variable_by_vector
- test_with_late_data_definition, test_with_new_data_definition, test_drop_variable
- test_orient[x-x], test_orient[y-y], test_orient[v-x], test_orient[h-y]

**TestScaling (22 failures):**
- test_inference, test_inference_from_layer_data, test_inference_joins
- test_inferred_categorical_converter, test_explicit_categorical_converter
- test_mark_data_log_transform_is_inverted, test_mark_data_log_transfrom_with_stat
- test_mark_data_from_categorical, test_mark_data_from_datetime
- test_computed_var_ticks, test_computed_var_transform
- test_explicit_range_with_axis_scaling, test_derived_range_with_axis_scaling
- test_facet_categories, test_facet_categories_unshared, test_facet_categories_single_dim_shared
- test_pair_categories, test_pair_categories_shared
- test_identity_mapping_linewidth, test_pair_single_coordinate_stat_orient
- test_inferred_nominal_passed_to_stat, test_identity_mapping_color_tuples

**TestPlotting (27 failures):**
- test_single_split_single_layer, test_single_split_multi_layer
- test_one_grouping_variable[color], test_one_grouping_variable[group]
- test_two_grouping_variables, test_facets_no_subgroups, test_facets_one_subgroup
- test_layer_specific_facet_disabling, test_paired_variables, test_paired_one_dimension
- test_paired_variables_one_subset, test_paired_and_faceted
- test_stat, test_move, test_stat_and_move, test_stat_log_scale, test_move_log_scale
- test_multi_move, test_multi_move_with_pairing, test_move_with_range
- test_on_axes, test_on_figure[True], test_on_figure[False]
- test_on_subfigure[True], test_on_subfigure[False]
- test_axis_labels_from_layer, test_axis_labels_are_first_name, test_labels_legend

**TestPairInterface (2 failures):**
- test_orient_inference, test_computed_coordinate_orient_inference

**TestLegend (13 failures):**
- test_single_layer_single_variable, test_single_layer_common_variable
- test_single_layer_common_unnamed_variable, test_single_layer_multi_variable
- test_multi_layer_single_variable, test_multi_layer_multi_variable
- test_multi_layer_different_artists, test_three_layers
- test_identity_scale_ignored, test_suppression_in_add_method
- test_anonymous_title, test_legendless_mark

All these tests were failing on the unpatched base (confirmed in r4_failbase_mwaskom__seaborn-3069.txt lines 46-121).

### Comparison to baseline

| Metric | Fail-on-base | Current (with patch) | Change |
|--------|--------------|----------------------|--------|
| Passed | 94 | 96 | +2 (the FAIL_TO_PASS tests) |
| Failed | 76 | 74 | -2 (the fixed tests) |
| XFail | 5 | 5 | 0 |

The patch successfully fixed exactly the two target tests with no regressions.

### Kill report

Not applicable - instance is resolved.

VERDICT: RESOLVED
RE-ENTER: none
