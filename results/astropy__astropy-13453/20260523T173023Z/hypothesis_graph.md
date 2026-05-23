# Hypothesis graph: astropy__astropy-13453

## H₀: Missing _set_col_formats() call (abduction)

**Evidence**: Test fails because HTML output shows unformatted values:
- `<td>1</td>` instead of `<td>0001</td>` (format "04d" ignored)
- `<td>1.234567e-11</td>` instead of `<td>1.23e-11</td>` (format ".2e" ignored)

**Root cause**: In `astropy/io/ascii/html.py`, the `HTML.write()` method (line 342) overrides the base writer and does not call `self.data._set_col_formats()` before using `col.info.iter_str_vals()`.

**Supporting code**:
- `core.py:1727`: `writer.data.formats = kwargs['formats']` - formats are passed in
- `core.py:1510`: `self.data.cols = new_cols` - base writer sets data.cols
- `core.py:907`: `self._set_col_formats()` - base str_vals() calls this
- `core.py:934-938`: `_set_col_formats()` applies formats by setting `col.info.format`
- `html.py:439,502`: Calls `col.info.iter_str_vals()` without having set formats first
- `html.py:354`: Calls `_set_fill_values()` but NOT `_set_col_formats()`

**Confidence**: Deduction - 98% (traced code path, compared to working formats in RST/CSV)


## Gate iteration 1

**Applied fix:**
```diff
--- a/astropy/io/ascii/html.py
+++ b/astropy/io/ascii/html.py
@@ -354,6 +354,8 @@ class HTML(core.BaseReader):
             self.data.fill_values = [self.data.fill_values]
 
         self.data._set_fill_values(cols)
+        self.data.cols = cols
+        self.data._set_col_formats()
 
         lines = []
```

**codex volley result:** Fix is correct for the failing test. Sets `self.data.cols` and calls `_set_col_formats()` to apply user-supplied formats before `col.info.iter_str_vals()` is called. No regressions detected.

**Gate result:** ✅ PASSED
```
PASSED astropy/io/ascii/tests/test_html.py::test_write_table_formatted_columns
======================== 10 passed, 16 skipped in 0.04s ========================
```

**Trajectory:** Convergent success — FAIL_TO_PASS test passes on first gate run.

**Status:** RESOLVED

---

## Audit: astropy__astropy-13453

### FAIL_TO_PASS
- `astropy/io/ascii/tests/test_html.py::test_write_table_formatted_columns`: **PASS** ✅

### PASS_TO_PASS regressions
None. All 9 PASS_TO_PASS tests remain passing:
- `test_listwriter`: PASS
- `test_htmlinputter_no_bs4`: PASS
- `test_multicolumn_write`: PASS
- `test_write_no_multicols`: PASS
- `test_write_table_html_fill_values`: PASS
- `test_write_table_html_fill_values_optional_columns`: PASS
- `test_write_table_html_fill_values_masked`: PASS
- `test_multicolumn_table_html_fill_values`: PASS
- `test_multi_column_write_table_html_fill_values_masked`: PASS

### Pre-existing (not counted, confirmed against base capture)
None.

### Verdict Summary
The patch resolves the issue completely:
- ✅ All FAIL_TO_PASS tests now pass (1/1)
- ✅ Zero PASS_TO_PASS regressions (0/9)
- ✅ No new failures introduced

The fix correctly applies user-supplied formats to HTML table columns by calling `_set_col_formats()` after setting `self.data.cols`, matching the pattern used by other writers.
