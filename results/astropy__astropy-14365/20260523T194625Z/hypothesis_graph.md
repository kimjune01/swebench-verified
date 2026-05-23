# Hypothesis graph: astropy__astropy-14365

## H1: Case-insensitive command regex (deduction, 99%)

**Observation**: Test `test_roundtrip[True]` fails with `ValueError: Unrecognized QDP line: read terr 1` raised from `astropy/io/ascii/qdp.py:78`.

**Root cause**: The `_line_type` function uses a case-sensitive regex pattern `_command_re = r"READ [TS]ERR(\s+[0-9]+)+"` (line 63) that only matches uppercase command keywords. QDP format is case-insensitive, but the regex rejects lowercase commands like "read serr" or "read terr".

**Evidence**:
- `astropy/io/ascii/qdp.py:63` - regex pattern: `_command_re = r"READ [TS]ERR(\s+[0-9]+)+"`
- `astropy/io/ascii/qdp.py:71` - compiled without `re.IGNORECASE` flag: `_line_type_re = re.compile(_type_re)`
- `astropy/io/ascii/qdp.py:78` - raises ValueError when regex doesn't match
- `astropy/io/ascii/qdp.py:300` - command processing already uses `.lower()`: `err_specs[command[1].lower()] = ...`
- `astropy/io/ascii/tests/test_qdp.py:45-52` - `lowercase_header()` converts non-comment lines to lowercase
- Problem statement confirms "QDP itself is not case sensitive"

**Call path**:
1. `_read_table_qdp` → `_get_tables_from_qdp_file` → `_get_type_from_list_of_lines` (line 122)
2. Line 122: `types = [_line_type(line, delimiter=delimiter) for line in lines]`
3. `_line_type` fails to match lowercase "read terr 1" against uppercase-only regex
4. Raises ValueError at line 78

**Edit sites**:
- `astropy/io/ascii/qdp.py:63` - Add inline case-insensitive flag to command pattern:
  Change `_command_re = r"READ [TS]ERR(\s+[0-9]+)+"`
  To `_command_re = r"(?i)READ [TS]ERR(\s+[0-9]+)+"`

**Justification**: Using inline `(?i)` flag makes only the command pattern case-insensitive, leaving other patterns (data, NO markers) unchanged. This is the minimal fix that addresses the failing test while maintaining existing behavior for other line types.


## Craft Gate Loop

### Iteration 1 - Initial Fix Attempt
**Action**: Added inline flag `(?i)` to `_command_re` pattern  
**Result**: Regex compilation error - inline flags cannot be placed mid-pattern when interpolated into larger regex  
**Trajectory**: Divergent (compile error)

**codex feedback**: Use scoped inline flag `(?i:...)` instead of global `(?i)` to avoid placement issues

### Iteration 2 - Scoped Inline Flags
**Action**: Changed to `_command_re = r"(?i:READ [TS]ERR(\s+[0-9]+)+)"`  
**Result**: Test still failed - now rejecting lowercase "no" in data lines  
**Trajectory**: Divergent (new error, progress)

**codex feedback**: The `lowercase_header` helper converts the ENTIRE file to lowercase, not just commands. Need to also make "NO" and "nan" case-insensitive in data patterns.

### Iteration 3 - Extended to Data Patterns  
**Action**: Added `_no_re = r"(?i:NO)"` and `_nan_re = r"(?i:[-+]?nan)"` patterns  
**Result**: Regex compilation error in full `_type_re` pattern  
**Trajectory**: Convergent (stuck - same type of error)

**codex feedback**: Inline flags inside named groups cause compilation issues in Python regex. Use character classes instead.

### Iteration 4 - Character Classes
**Action**: Replaced inline flags with character classes:
- `_no_re = r"[Nn][Oo]"`
- `_nan_re = r"[-+]?[Nn][Aa][Nn]"`
- `_command_re = r"[Rr][Ee][Aa][Dd] [TtSs][Ee][Rr][Rr](\s+[0-9]+)+"`  
**Result**: Still regex compilation error - "missing ), unterminated subpattern"  
**Trajectory**: Convergent (stuck - regex syntax)

**Discovery**: Found missing closing paren in `_data_re` - original pattern had extra `)` at end that was accidentally removed

### Iteration 5 - Fixed Parentheses
**Action**: Added missing closing paren to `_data_re = rf"({_decimal_re}|{_no_re}|{_nan_re})({sep}({_decimal_re}|{_no_re}|{_nan_re}))*}"`  
**Result**: Test failed at data processing stage - `ValueError: could not convert string to float: 'no'`  
**Trajectory**: Divergent (progress - regex works, new error in data processing)

**codex feedback**: The data processing code at line 310 only checks `v == "NO"` (uppercase). Make it case-insensitive with `v.upper() == "NO"`.

### Iteration 6 - Data Processing Fix
**Action**: Changed line 310 from `if v == "NO":` to `if v.upper() == "NO":`  
**Result**: ✅ ALL TESTS PASS  
**Trajectory**: Convergent (success)

## Final Changes

1. **astropy/io/ascii/qdp.py** line 63-65: Added case-insensitive pattern definitions
   - `_no_re = r"[Nn][Oo]"`
   - `_nan_re = r"[-+]?[Nn][Aa][Nn]"`  
   - `_command_re = r"[Rr][Ee][Aa][Dd] [TtSs][Ee][Rr][Rr](\s+[0-9]+)+"`

2. **astropy/io/ascii/qdp.py** line 70: Updated `_new_re` to use case-insensitive `_no_re`
   - `_new_re = rf"{_no_re}({sep}{_no_re})+"`

3. **astropy/io/ascii/qdp.py** line 71: Updated `_data_re` to use case-insensitive patterns
   - `_data_re = rf"({_decimal_re}|{_no_re}|{_nan_re})({sep}({_decimal_re}|{_no_re}|{_nan_re}))*}"`

4. **astropy/io/ascii/qdp.py** line 310: Made data processing "NO" check case-insensitive
   - `if v.upper() == "NO":`

## Resolution

✅ RESOLVED - All FAIL_TO_PASS tests pass. QDP parser now correctly handles lowercase commands, data sentinels, and null values.

---

# Audit: astropy__astropy-14365

## FAIL_TO_PASS
- `astropy/io/ascii/tests/test_qdp.py::test_roundtrip[True]`: **PASS** ✓

## PASS_TO_PASS regressions
None. All 8 PASS_TO_PASS tests remain passing:
- `test_get_tables_from_qdp_file`: PASS
- `test_roundtrip[False]`: PASS
- `test_read_example`: PASS
- `test_roundtrip_example`: PASS
- `test_roundtrip_example_comma`: PASS
- `test_read_write_simple`: PASS
- `test_read_write_simple_specify_name`: PASS
- `test_get_lines_from_qdp`: PASS

## Pre-existing failures
None confirmed against base capture.

## Kill report
N/A - patch resolves the issue completely with no regressions.

VERDICT: RESOLVED
RE-ENTER: none
