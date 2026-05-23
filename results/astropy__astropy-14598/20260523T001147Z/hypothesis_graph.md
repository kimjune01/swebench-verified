# Hypothesis graph: astropy__astropy-14598

## H0: Double-unescape bug in CONTINUE card parsing (ABDUCTION - 85%)

**Observation**: Test fails with assertion error - when a Card with a long string value containing '' is serialized to string and parsed back, one single quote is lost.

**Root cause**: Single quotes are being unescaped twice:
1. First in `_split()` method at line 862: `value = value.rstrip().replace("''", "'")`
2. Second in `_parse_value()` method at line 771: `value = re.sub("''", "'", m.group("strg"))`

**How it happens**:
- Original value: "x" * 65 + "''" (67 chars total)
- Escaped for FITS: "x" * 65 + "'''' (69 chars - each ' becomes '')
- Split into chunks by `_words_group(value, 67)`: ["x"*65 + "''", "''"]
- Formatted as CONTINUE cards:
  - Card 0: `CONFIG  = 'xxxxx(65 x's)''&'`
  - Card 1: `CONTINUE  ''''`
  
- When parsing back, `_split()` processes each subcard:
  - Card 0 string: "xxxxx(65 x's)''" → after replace → "xxxxx(65 x's)'"
  - Card 1 string: "'''' → after replace → "''"
  - Joined: "xxxxx(65 x's)'" + "''" = "xxxxx(65 x's)'''"
  - Wrapped: "'xxxxx(65 x's)'''" (3 single quotes inside)
  
- Then `_parse_value()` unescapes again:
  - "xxxxx(65 x's)'''" → after replace → "xxxxx(65 x's)'" (1 single quote instead of 2)

**Evidence**:
- `astropy/io/fits/card.py:862` - First unescape in `_split()`
- `astropy/io/fits/card.py:771` - Second unescape in `_parse_value()`
- Git history shows commit c5400c7332 refactored CONTINUE handling into `_split()` but kept the unescape logic, causing double-unescaping

**Confidence**: 85% (abduction) - The code path is clear and the double-unescape is confirmed by tracing through the logic. This explains why the bug only occurs for long strings (requiring CONTINUE cards) and at specific lengths (where '' gets split across chunks).


## Craft Phase Gate Loop

### Iteration 1: Initial Fix Attempt
**Hypothesis**: Remove double-unescaping by removing `.replace("''", "'")` from `_split()` at line 862.

**Changes**:
- Modified `astropy/io/fits/card.py` line 862: `value = value.rstrip().replace("''", "'")` → `value = value.rstrip()`

**Gate Result**: FAILED  
Test `test_long_string_value_with_quotes` failed on third case (`"x"*100 + "'' xxx"`)  
Error: `assert "xxxxxxxxxxxx...xxxxxxxxxxx''" == "xxxxxxxxxxxx...xxxxxxx'' xxx"`  
The string lost " xxx" (space + xxx) at the end.

**Analysis**: The fix exposed a second bug - the regex `_strg_comment_RE` was missing a `$` anchor, causing it to match only a prefix of the string and lose trailing content.

### Iteration 2: Add Missing Regex Anchor
**Hypothesis**: The regex `_strg_comment_RE` needs a `$` anchor to match the entire string, not just a prefix.

**Changes**:
- Modified `astropy/io/fits/card.py` line 69: `_strg_comment_RE = re.compile(f"({_strg})? *{_comm_field}?")` → `_strg_comment_RE = re.compile(f"({_strg})? *{_comm_field}?$")`

**Gate Result**: FAILED  
Error: `assert "xxxxxxxxxxxx...xxxxxxxxxxxx'" == "xxxxxxxxxxxx...xxxxxxxxxxx''"`  
Now getting ONE quote instead of TWO (different failure).

**Analysis**: The first fix wasn't actually applied due to shell escaping issues in the sed command. The `.replace("''", "'")` was still present, causing a single unescape instead of double-unescape.

### Iteration 3: Properly Apply First Fix
**Hypothesis**: Need to correctly remove the `.replace("''", "'")` from line 862.

**Changes**:
- Used Python script to properly remove `.replace("''", "'")` from line 862

**Gate Result**: PASSED ✓  
All 176 tests passed, including `test_long_string_value_with_quotes`.

**Final Fix Summary**:
Two changes required:
1. **Line 69**: Add `$` anchor to `_strg_comment_RE` regex to ensure full string matching
2. **Line 862**: Remove `.replace("''", "'")` from value processing in `_split()` to eliminate double-unescaping

**Root Cause Confirmed**: Double-unescaping of single quotes in CONTINUE card parsing:
- First unescape was at line 862 in `_split()` 
- Second unescape at line 771 in `_parse_value()`
- The regex also needed anchoring to match complete strings

**Iterations**: 3  
**Status**: RESOLVED

## Audit Phase

**Test Environment**: Offline container with craft patch applied

**Patch Verification**:
```diff
diff --git a/astropy/io/fits/card.py b/astropy/io/fits/card.py
@@ -66,7 +66,7 @@ class Card(_Verify):
-    _strg_comment_RE = re.compile(f"({_strg})? *{_comm_field}?")
+    _strg_comment_RE = re.compile(f"({_strg})? *{_comm_field}?$")
 
@@ -859,7 +859,7 @@ class Card(_Verify):
-                value = value.rstrip().replace("''", "'")
+                value = value.rstrip()
```

### FAIL_TO_PASS Results

- `astropy/io/fits/tests/test_header.py::TestHeaderFunctions::test_long_string_value_with_quotes`: **PASS** ✓

### PASS_TO_PASS Regressions

**None** — All 176 tests in the suite passed with no regressions.

Sample verification of PASS_TO_PASS tests:
- `test_shallow_copy`: PASS ✓
- `test_init_with_header`: PASS ✓
- `test_init_with_dict`: PASS ✓
- `test_rename_keyword`: PASS ✓
- `test_string_value_card`: PASS ✓

### Pre-existing Failures

**None** — No tests failed on base or after patch application beyond the expected FAIL_TO_PASS case.

### Gate Output Summary

```
============================= 176 passed in 0.37s ==============================
```

All tests passed, including:
- The FAIL_TO_PASS test that was previously failing
- All PASS_TO_PASS tests specified in the contract
- The complete test suite with zero regressions

