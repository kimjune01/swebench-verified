# Hypothesis graph: astropy__astropy-14182

## H₀: Missing header_rows parameter in RST.__init__()
**Type:** Abduction  
**Confidence:** 95% (Deduction - traced code path)

### Observation
Test `test_rst_with_header_rows` fails with:
```
TypeError: __init__() got an unexpected keyword argument 'header_rows'
```

The error occurs at `astropy/io/ascii/core.py:1692` when trying to instantiate the RST reader class with `header_rows=['name', 'unit', 'dtype']`.

### Root Cause
The `RST` class (in `astropy/io/ascii/rst.py:35`) overrides `__init__()` without accepting the `header_rows` parameter, while its parent class `FixedWidth` does support this parameter.

**Current RST.__init__():**
```python
def __init__(self):
    super().__init__(delimiter_pad=None, bookend=False)
```

**Parent FixedWidth.__init__() signature:**
```python
def __init__(
    self,
    col_starts=None,
    col_ends=None,
    delimiter_pad=" ",
    bookend=True,
    header_rows=None,
):
```

The parent class properly handles `header_rows` by:
1. Setting `self.header.header_rows = header_rows`
2. Setting `self.data.header_rows = header_rows`
3. Adjusting `self.data.start_line` if needed

### Supporting Evidence
- `astropy/io/ascii/rst.py:61` - RST.__init__() has no header_rows parameter
- `astropy/io/ascii/fixedwidth.py:339-354` - FixedWidth accepts and processes header_rows
- `astropy/io/ascii/fixedwidth.py:475-487` - FixedWidthTwoLine shows the pattern for handling header_rows in subclasses
- `astropy/io/ascii/fixedwidth.py:102` - FixedWidthHeader.get_cols() expects header_rows attribute
- `astropy/io/ascii/fixedwidth.py:261-263` - FixedWidthData.write() uses header_rows for output

### Edit Sites Required

**File:** `astropy/io/ascii/rst.py`  
**Lines:** 61-62 (RST.__init__ method)

1. **Change the method signature** to accept `header_rows` parameter
2. **Pass header_rows to parent** via `super().__init__()`  
3. **Adjust data.start_line** for RST format structure

For RST format with N header rows:
- Line 0: position line (top separator with `=`)
- Lines 1 to N: header rows
- Line N+1: middle separator (another line of `=`)
- Lines N+2 onward: data

Therefore: `data.start_line = len(header_rows) + 2`

With default 1 header row: 1 + 2 = 3 ✓ (matches current hardcoded value)  
With 3 header rows: 3 + 2 = 5 ✓ (matches test expectation)

### Related Components (no changes needed)
- `SimpleRSTHeader` (lines 16-27): Inherits header_rows handling from FixedWidthHeader
- `SimpleRSTData` (lines 29-33): Uses `end_line = -1` (relative to end), works with any header_rows count
- `RST.write()` (lines 63-66): Delegates to parent, which properly handles header_rows


## Craft: Gate Loop

### Iteration 1: Initial volley with codex

**Drafted fix v1:**
- Updated `RST.__init__` to accept `header_rows=None`
- Passed `header_rows` to `super().__init__()`
- Set `self.data.start_line = len(self.header.header_rows) + 2` in `__init__`

**Codex feedback v1:**
- Identified that `write()` method also needs updating - hardcoded `lines[1]` for separator won't work with multiple header rows
- Suggested updating `write()` to compute separator index dynamically

### Iteration 2: Second volley

**Drafted fix v2:**
- Added `write()` fix to compute separator: `sep = lines[len(self.header.header_rows)]`
- Used `self.data.header_rows` in `__init__`

**Codex feedback v2:**
- Identified timing issue: `header_rows` might be set after `__init__`, so computing `start_line` in `__init__` is too early
- Recommended moving `start_line` computation to a `read()` method override
- Referenced FixedWidthTwoLine pattern

### Iteration 3: Third volley (final)

**Drafted fix v3:**
- Moved `start_line` computation from `__init__` to new `read()` method
- Kept `write()` fix with dynamic separator index
- Followed FixedWidthTwoLine pattern of computing from `self.header.header_rows` after super()

**Codex feedback v3:**
- Approved the pattern as robust
- Confirmed it handles both construction-time and runtime `header_rows` changes

**Applied fix:**
```python
def __init__(self, header_rows=None):
    super().__init__(delimiter_pad=None, bookend=False, header_rows=header_rows)

def read(self, table):
    self.data.start_line = len(self.header.header_rows) + 2
    return super().read(table)

def write(self, lines):
    lines = super().write(lines)
    sep = lines[len(self.header.header_rows)]
    lines = [sep] + lines + [sep]
    return lines
```

### Gate result: PASS

All tests pass (10/10):
- `test_rst_with_header_rows` ✓ (target FAIL_TO_PASS)
- All existing tests ✓ (no regressions)

**Resolution:** The fix correctly handles multiple header rows by:
1. Accepting `header_rows` parameter in `__init__` and passing to parent
2. Computing `data.start_line` dynamically in `read()` based on actual header row count
3. Computing separator line index dynamically in `write()` based on header row count

The formula `len(header_rows) + 2` accounts for RST format structure:
- Line 0: top separator
- Lines 1-N: header rows
- Line N+1: middle separator
- Lines N+2+: data rows

## Audit: astropy__astropy-14182

### FAIL_TO_PASS
- test_rst_with_header_rows: PASS ✓

### PASS_TO_PASS regressions
none

### Pre-existing (not counted, confirmed against base capture)
none

### Gate result
All 10 tests passed:
- 1/1 FAIL_TO_PASS test now passing
- 9/9 PASS_TO_PASS tests still passing
- 0 regressions introduced

The patch successfully resolves the issue by:
1. Accepting `header_rows` parameter in `RST.__init__()` and forwarding to parent `FixedWidth`
2. Dynamically computing `data.start_line` in `read()` based on header row count
3. Dynamically computing separator line index in `write()` for proper formatting

