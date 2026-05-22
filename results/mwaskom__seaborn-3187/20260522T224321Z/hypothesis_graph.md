# Hypothesis graph: mwaskom__seaborn-3187

## Hypothesis Node: Recon R1

**Type**: Abduction → Deduction (95% confidence)

**Failure Summary**:
Both tests create data with values in the range of 1e8 and expect legend text to show these large values (> 1e7). Instead:
- Test 1 (Plot API): legend shows "1" instead of ~100000001
- Test 2 (relplot API): legend shows "2.5" instead of ~100000002.5

**Root Cause**:
matplotlib's ScalarFormatter uses an offset for large numeric ranges to keep axis labels concise. When values are large (e.g., 100000001, 100000002), it displays "1", "2" with a separate "+1e8" offset indicator. The methods `format_ticks()` and `__call__()` return only the offset-stripped labels ("1", "2"), not the full values. Seaborn's legend code uses these methods without accounting for the offset, resulting in incorrect legend labels.

**Evidence**:
1. `seaborn/_core/scales.py:381` - New objects API path:
   ```python
   labels = axis.major.formatter.format_ticks(locs)
   ```
   When `locs = [1e8+1, 1e8+2, ...]`, this returns `['1', '2', ...]` if formatter has offset

2. `seaborn/utils.py:709` - Old relational API path:
   ```python
   formatted_levels = [formatter(x) for x in raw_levels]
   ```
   Same issue: `formatter(x)` strips the offset

3. Verified formatter behavior:
   - `formatter.get_offset()` returns "+1e8" when offset is present
   - `formatter.format_ticks([1e8+1, 1e8+2])` returns `['1', '2']` 
   - `formatter.format_data(1e8+1)` returns `'1.00000001e8'` (full value)
   - All Formatter types have `get_offset()`, returns `''` when no offset

**Edit Sites**:
1. `seaborn/_core/scales.py` lines 376-382 (legend creation in ContinuousBase._setup):
   - Check if `axis.major.formatter.get_offset()` is non-empty
   - If offset exists, use `[formatter.format_data(loc) for loc in locs]`
   - Otherwise, use `formatter.format_ticks(locs)` as before

2. `seaborn/utils.py` lines 700-709 (locator_to_legend_entries function):
   - Check if `formatter.get_offset()` is non-empty after `formatter.set_locs()`
   - If offset exists, use `[formatter.format_data(x) for x in raw_levels]`
   - Otherwise, use `[formatter(x) for x in raw_levels]` as before

**Confidence**: Deduction - 95%
- Code path traced from test to failure point
- Formatter behavior verified experimentally
- Fix tested and produces correct parseable values
- Both API paths identified and localized


## Gate Loop - Iteration 1

**Action**: Applied fix to both edit sites:
- `seaborn/_core/scales.py`: Added `formatter.set_locs(locs)` before `get_offset()` check, use `format_data_short()` when offset present
- `seaborn/utils.py`: Added offset check, use `format_data_short()` when offset present

**Codex volley**: Confirmed implementation is directionally correct. Key feedback:
- Must call `set_locs()` before `get_offset()` (offset computed during set_locs)
- Use `format_data_short()` not `format_data()` for parseability (avoids LaTeX strings)

**Gate result**: ✅ PASSED
- tests/_core/test_plot.py::TestLegend::test_legend_has_no_offset - PASSED
- tests/test_relational.py::TestRelationalPlotter::test_legend_has_no_offset - PASSED
- 251 passed, 5 xfailed, 207 warnings

**Resolution**: Both FAIL_TO_PASS tests pass. The fix correctly uses `format_data_short()` to get full numeric values when formatter has an offset, instead of the offset-stripped values from `format_ticks()` or `__call__()`.

## Audit: mwaskom__seaborn-3187

**Patch confirmed live**: 2 files modified, 12 lines changed (seaborn/_core/scales.py, seaborn/utils.py)

**Gate execution**: 251 passed, 5 xfailed (expected failures), 0 new failures

### FAIL_TO_PASS Analysis
- ✅ tests/_core/test_plot.py::TestLegend::test_legend_has_no_offset: **PASSED**
- ✅ tests/test_relational.py::TestRelationalPlotter::test_legend_has_no_offset: **PASSED**

Both target tests now pass. The fix successfully addresses the legend offset issue.

### PASS_TO_PASS Regressions
**None.** All 249 PASS_TO_PASS tests remain passing. No regressions introduced by the patch.

### Pre-existing Failures (not counted)
The 5 XFAIL tests were already marked as expected failures on base:
- test_stat_default (Need decision on default stat)
- test_categorical_as_datetime (Temporal auto-conversion not implemented)
- test_log_scale_name (Custom log scale needs log name)
- test_identity_mapping_color_strings (Color identity scale representation undefined)
- test_undefined_variable_raises (Unused variable scale behavior undefined)

These are known issues unrelated to the legend offset fix.

### Verdict Summary
- ✅ All FAIL_TO_PASS pass (2/2)
- ✅ Zero PASS_TO_PASS regressions (0/249)
- ✅ Patch correctly handles formatter offset in both code paths
- ✅ No breaking changes detected

**Final Status**: The patch is complete and correct. Both failing tests are fixed with no regressions.

VERDICT: RESOLVED
RE-ENTER: none
