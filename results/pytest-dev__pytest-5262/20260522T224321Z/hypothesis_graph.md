# Hypothesis graph: pytest-dev__pytest-5262

## H₀: Initial observation (abduction)
The test `test_capfd_sys_stdout_mode` fails because `sys.stdout.mode` contains 'b', reporting 'rb+' instead of a text mode.

**Evidence:**
- Test: `testing/test_capture.py:1055` - `assert "b" not in sys.stdout.mode`
- Failure: `AssertionError: assert 'b' not in 'rb+'`

## H₁: Root cause (deduction)
`EncodedFile` incorrectly exposes the underlying binary buffer's mode via `__getattr__`.

**Code path:**
1. `safe_text_dupfile()` (src/_pytest/capture.py:406-422) creates a binary file descriptor and wraps it in `EncodedFile`
2. Line 418-420: The mode has 'b' appended (`if "b" not in mode: mode += "b"`)
3. Line 421: Opens with binary mode: `f = os.fdopen(newfd, mode, 0)`
4. Line 422: Wraps in `EncodedFile(f, encoding)`
5. `EncodedFile.__getattr__` (line 450-451) delegates `mode` attribute to the underlying buffer

**Contract violation:**
- `EncodedFile.write()` (line 432-439) expects `str` in Python 3, raises `TypeError` for `bytes`
- But `mode` attribute reports 'rb+' (binary), misleading callers like youtube-dl
- External code checks `'b' in mode` to decide whether to write bytes or strings
- This causes them to write bytes to a text stream, triggering the TypeError

**Supporting evidence:**
- `src/_pytest/capture.py:425-451` - EncodedFile class definition
- `src/_pytest/capture.py:432-439` - write() method contract (str only in PY3)
- `testing/test_capture.py:1559-1578` - test_typeerror_encodedfile_write confirms bytes raise TypeError
- Precedent: `name` property (line 445-448) already overrides buffer attribute

**Confidence:** Deduction - 98% (traced from test through __getattr__ to buffer.mode)

## Edit sites
1. `src/_pytest/capture.py` lines 445-451 (after the `name` property, before `__getattr__`):
   - Add a `mode` property that returns `self.buffer.mode` with 'b' removed
   - Strip 'b' from the mode string to report text mode (e.g., 'rb+' → 'r+')

## craft gate-loop (iteration 1)

**Hypothesis**: Add `mode` property to `EncodedFile` that returns `self.buffer.mode.replace("b", "")` — follows existing `name` property pattern.

**Edit**: `src/_pytest/capture.py` lines 448-452 — inserted `@property def mode(self):` that strips 'b' from buffer mode.

**Gate result**: ✅ GREEN
- FAIL_TO_PASS test now passes: `testing/test_capture.py::TestFDCapture::test_capfd_sys_stdout_mode`
- 108 passed, 7 skipped, 1 xfailed, 0 failed
- No regressions

**Resolution**: The fix correctly addresses the root cause. `EncodedFile` now presents a text-mode interface via the `mode` property, preventing external code from incorrectly treating it as binary.

## Audit: pytest-dev__pytest-5262

**Patch confirmed live**: 5 lines added to `src/_pytest/capture.py` (mode property added to EncodedFile)

### FAIL_TO_PASS
- `testing/test_capture.py::TestFDCapture::test_capfd_sys_stdout_mode`: **PASSED** ✓

### PASS_TO_PASS regressions
None. All 108 tests passed.

### Pre-existing (not counted, confirmed against base capture)
None. The only failure on base was the FAIL_TO_PASS test, which now passes.

### Kill report
Not applicable — fix is RESOLVED.

**VERDICT**: RESOLVED
**RE-ENTER**: none
