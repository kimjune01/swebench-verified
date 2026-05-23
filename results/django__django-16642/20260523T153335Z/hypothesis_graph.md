# Hypothesis graph: django__django-16642

## H₀: Missing encoding mappings (abduction)
**Date:** 2026-05-23
**Status:** Active hypothesis

The tests fail because FileResponse's encoding-to-MIME-type mapping dictionary is missing entries for "br" (Brotli) and "compress" (Unix compress) encodings.

**Evidence:**
1. Test failure shows `.tar.br` returns `application/x-tar` instead of expected `application/x-brotli`
2. Test failure shows `.tar.Z` returns `application/x-tar` instead of expected `application/x-compress`
3. `mimetypes.guess_type("test.tar.br")` returns `("application/x-tar", "br")`
4. `mimetypes.guess_type("test.tar.Z")` returns `("application/x-tar", "compress")`
5. The dictionary at `django/http/response.py:611-615` only contains: `{"bzip2": "application/x-bzip", "gzip": "application/gzip", "xz": "application/x-xz"}`
6. The `.get(encoding, content_type)` call falls back to `content_type` when encoding is not in dict

**Root cause:**
When `mimetypes.guess_type()` returns encoding="br" or encoding="compress", the dictionary lookup fails and falls back to the base content_type ("application/x-tar"), which is incorrect for compressed files.

**Fix:**
Add two missing entries to the dictionary:
- `"br": "application/x-brotli"`
- `"compress": "application/x-compress"`

**Confidence:** Deduction - 95%
This is a simple missing-key problem directly observable in the code.

## Craft gate loop

### Iteration 1: Initial fix

**Change applied:**
Added two missing entries to the encoding-to-MIME-type dictionary in `django/http/response.py` lines 615-616:
- `"br": "application/x-brotli"` for Brotli compression
- `"compress": "application/x-compress"` for Unix compress (.Z files)

**codex pre-gate review:**
"No blocking issue in the proposed hunk. It addresses the real gap: `mimetypes.guess_type()` returns encodings `br` and `compress`, and `FileResponse` currently falls back to `application/x-tar`."

**Gate result:**
✅ PASS - All 22 tests passed, including `test_compressed_response`

**Resolution:**
The fix correctly maps Brotli (`.br`) and Unix compress (`.Z`) file encodings to their proper MIME types, matching the existing behavior for gzip, bzip2, and xz. FAIL_TO_PASS tests now pass.

## Audit: django__django-16642

### FAIL_TO_PASS
- test_compressed_response (If compressed responses are served with the uncompressed Content-Type): **PASS** ✓

### PASS_TO_PASS regressions
None. All 22 tests pass.

### Pre-existing failures (not counted)
None. The baseline showed `.tar.br` and `.tar.Z` subtests failing; now all pass.

### Gate output
All 22 tests in `responses.test_fileresponse` passed in 0.004s.

**Full contract met:**
- All FAIL_TO_PASS tests now pass
- Zero PASS_TO_PASS regressions
- Fix correctly maps Brotli and Unix compress encodings to proper MIME types

VERDICT: RESOLVED
RE-ENTER: none
