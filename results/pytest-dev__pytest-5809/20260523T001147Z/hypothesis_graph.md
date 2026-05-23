# Hypothesis graph: pytest-dev__pytest-5809

## H₁: Incorrect lexer parameter in pastebin upload
**Type**: Root cause (abduction → deduction)
**Status**: Active hypothesis
**Confidence**: 99% (deduction - direct code reading)

### Evidence
- Test file `testing/test_pastebin.py:135` specifies `lexer = "text"`
- Test assertion at line 139 checks that data contains `"lexer=text"`
- Implementation at `src/_pytest/pastebin.py:82` uses `"lexer": "python3" if sys.version_info[0] >= 3 else "python"`
- Problem statement confirms that using `lexer=python3` causes HTTP 400 errors on bpaste.net
- Problem statement confirms that changing to `lexer=text` fixes the issue

### Root cause
The `create_new_paste()` function incorrectly treats pytest console output as Python code by setting the lexer to "python3" or "python". Pytest output contains test results, tracebacks, and arbitrary console text - not Python source code. The bpaste.net service rejects certain content patterns when submitted with a Python lexer, resulting in HTTP 400 errors.

### Code path
1. Test calls `pastebin.create_new_paste(b"full-paste-contents")`
2. Function at `src/_pytest/pastebin.py:68-88` constructs params dict with `"lexer": "python3"`
3. urlopen sends this to bpaste.net at line 86
4. For certain content (per problem statement), bpaste.net returns HTTP 400
5. Test expects `"lexer=text"` in the submitted data, but implementation sends `"lexer=python3"`

### Edit site
- `src/_pytest/pastebin.py` line 82: Change from `"lexer": "python3" if sys.version_info[0] >= 3 else "python",` to `"lexer": "text",`


## Craft: Gate iteration 1

**Change applied**: Modified `src/_pytest/pastebin.py` line 82 to use `"lexer": "text"` instead of conditional Python version check.

**Codex pre-gate review**: Findings: none. Approved with no issues identified.

**Gate result**: PASS
- `testing/test_pastebin.py::TestPaste::test_create_new_paste` - PASSED ✓
- All 4 pastebin tests passed

**Trajectory**: Convergent (resolution) - FAIL_TO_PASS test now passes on first iteration.

**Resolution**: The fix was exactly as diagnosed by recon. Changing the lexer parameter from `"python3"/"python"` to `"text"` resolves the issue because pytest console output is plain text, not Python source code.


## Audit: Final verification

**Patch status**: ✓ Live in tree
- `src/_pytest/pastebin.py` line 82: `"lexer": "text"` (1 insertion, 1 deletion)

**Gate results**: All 4 tests PASSED

### FAIL_TO_PASS
- testing/test_pastebin.py::TestPaste::test_create_new_paste: **PASS** ✓

### PASS_TO_PASS  
- testing/test_pastebin.py::TestPasteCapture::test_failed: **PASS** ✓
- testing/test_pastebin.py::TestPasteCapture::test_all: **PASS** ✓
- testing/test_pastebin.py::TestPasteCapture::test_non_ascii_paste_text: **PASS** ✓

### Regressions
none

### Pre-existing failures
none

**Classification**: The FAIL_TO_PASS test now passes, all PASS_TO_PASS tests remain passing, zero regressions introduced. The fix is minimal and surgical.

**VERDICT**: RESOLVED  
**RE-ENTER**: none
