# Hypothesis graph: pytest-dev__pytest-7521

## H₀ (abduction, 2026-05-22)

**Symptom**: Tests fail because `capfd.readouterr()` converts `\r` and `\r\n` to `\n`.

**Root cause**: When `EncodedFile` (which inherits from `io.TextIOWrapper`) is instantiated in `FDCaptureBinary.__init__()` at line 386, the `newline` parameter is not specified. According to Python's documentation, when `newline` is `None` (the default), universal newlines mode is enabled, which translates all newline characters (`\r`, `\r\n`, `\n`) to `\n` on input.

**Evidence**:
- `src/_pytest/capture.py:386-392` — `EncodedFile` instantiation without `newline` parameter
- `src/_pytest/capture.py:195` — `CaptureIO` (which works correctly) uses `newline=""` to disable newline translation
- `git show 29e4cb5d4` — commit that changed `EncodedFile` from a custom class to `io.TextIOWrapper` subclass, introducing this regression

**Confidence**: Deduction — 98% (directly traced the code path and identified the missing parameter)

**Edit site**:
- `src/_pytest/capture.py:386-392` — Add `newline=""` parameter to `EncodedFile` instantiation to preserve original line endings

**Supporting code quotes**:
```python
# Line 386-392 (current, incorrect):
self.tmpfile = EncodedFile(
    TemporaryFile(buffering=0),
    encoding="utf-8",
    errors="replace",
    write_through=True,
)

# Line 195 (CaptureIO, correct):
super().__init__(io.BytesIO(), encoding="UTF-8", newline="", write_through=True)
```

## Craft gate loop

### Iteration 1: Draft and volley

**Draft:** Add `newline=""` parameter to `EncodedFile` instantiation at line 386 in `src/_pytest/capture.py`.

**Volley with codex:** codex confirmed no blocking issues. The fix is technically sound - `newline=""` disables universal newlines mode which was normalizing all line endings to `\n`. codex noted this matches the `CaptureIO` pattern and is correct.

**Applied fix:**
```diff
--- a/src/_pytest/capture.py
+++ b/src/_pytest/capture.py
@@ -386,6 +386,7 @@@ class FDCaptureBinary(FDCapture[bytes]):
             self.tmpfile = EncodedFile(
                 # TODO: Remove type ignore, fixed in next mypy release.
                 TemporaryFile(buffering=0),  # type: ignore[arg-type]
                 encoding="utf-8",
+                newline="",
                 errors="replace",
                 write_through=True,
             )
```

**Gate result:** GREEN
- All 125 tests in testing/test_capture.py passed
- Specifically verified FAIL_TO_PASS tests:
  - `testing/test_capture.py::TestCaptureFixture::test_cafd_preserves_newlines[\r\n]` - PASSED
  - `testing/test_capture.py::TestCaptureFixture::test_cafd_preserves_newlines[\r]` - PASSED

**E-value:** Convergent success - first attempt achieved resolution.

**Resolution:** The recon diagnosis was correct. Adding `newline=""` to the `EncodedFile` instantiation disables universal newlines mode, preserving original line endings (`\r`, `\r\n`, `\n`) exactly as written. This matches the behavior of `CaptureIO` which already uses `newline=""`.

---

# Audit: pytest-dev__pytest-7521

## Phase 1: Patch confirmation
```
git diff --stat:
 src/_pytest/capture.py | 1 +
 1 file changed, 1 insertion(+)
```
✓ Patch is live

## Phase 2: Gate execution
Gate ran successfully: **125 passed, 3 skipped, 1 xfailed in 4.38s**

## Phase 3: Classification

### FAIL_TO_PASS tests (must now PASS)
- `testing/test_capture.py::TestCaptureFixture::test_cafd_preserves_newlines[\r\n]` — **PASSED** ✓
- `testing/test_capture.py::TestCaptureFixture::test_cafd_preserves_newlines[\r]` — **PASSED** ✓

### PASS_TO_PASS regressions
**None** — all 125 tests passed, including:
- `testing/test_capture.py::TestCaptureFixture::test_cafd_preserves_newlines[\n]` — PASSED (confirmed explicitly)
- All other PASS_TO_PASS tests from baseline — PASSED

### Pre-existing (not counted, confirmed against base capture)
- 3 skipped tests (lsof unavailable, Windows-only) — expected
- 1 xfailed test (unimplemented feature) — expected

## Phase 4: Verdict

**Contract fulfilled:**
- ✓ All FAIL_TO_PASS tests now pass (2/2)
- ✓ Zero PASS_TO_PASS regressions (125 tests passed)

**Fix analysis:**
The patch adds `newline=""` to `EncodedFile` instantiation in `FDCaptureBinary.__init__()` (line 391), disabling Python's universal newlines mode. This preserves original line endings (`\r`, `\r\n`, `\n`) instead of normalizing them to `\n`. The fix is minimal, surgical, and matches the existing pattern in `CaptureIO` (line 195).

VERDICT: RESOLVED
RE-ENTER: none
