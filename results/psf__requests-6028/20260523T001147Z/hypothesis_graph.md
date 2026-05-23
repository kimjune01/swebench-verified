# Hypothesis graph: psf__requests-6028

## H₀: Initial Diagnosis (Abduction - 95%)

**Timestamp**: First recon pass

**Observation**: Tests `test_prepend_scheme_if_needed` fail for URLs containing authentication credentials:
- Input: `http://user:pass@example.com/path?query` → Output: `http://example.com/path?query` (auth stripped)
- Input: `http://user@example.com/path?query` → Output: `http://example.com/path?query` (auth stripped)

**Root Cause**: In commit `ef59aa02` (Aug 2021), `prepend_scheme_if_needed` was refactored from using stdlib's `urlparse` to urllib3's `parse_url`. The urllib3 version separates authentication credentials into a distinct `auth` field and removes them from the `netloc` field. However, the code extracts the `auth` value but never uses it when reconstructing the URL via `urlunparse`, resulting in credential loss.

**Evidence**:
- `requests/utils.py:966-982`: Function extracts `auth` from `parse_url(url)` but only uses `parsed.netloc` (which excludes auth) when calling `urlunparse`
- Manual testing confirms `parse_url('http://user:pass@example.com/path?query').netloc == 'example.com'` (no auth)
- Manual testing confirms `parse_url('http://user:pass@example.com/path?query').auth == 'user:pass'` (auth extracted separately)
- Git history shows the regression was introduced when switching from `urlparse` (which includes auth in netloc) to `parse_url` (which separates them)
- Similar auth reconstruction pattern exists in `requests/models.py:410-415` which correctly rebuilds netloc from auth+host+port

**Edit Site**: `requests/utils.py`, after line 973, add:
```python
if auth:
    netloc = f'{auth}@{netloc}'
```

This must be placed after the netloc swap logic (lines 972-973) but before the `urlunparse` call (line 982).

**Status**: High confidence - deduction from code reading, manual testing confirms fix, and git history shows clear regression point.


## Craft gate-loop node 1

**Action**: Applied fix to `requests/utils.py` at line 976:
```python
if auth:
    netloc = "%s@%s" % (auth, netloc)
```

**Volley**: codex reviewed and confirmed:
- Logic is correct for reconstructing netloc with auth
- Used `%` formatting for Python < 3.6 compatibility
- No double-auth bug (parse_url's netloc excludes auth)

**Gate result**: ✅ PASS
- FAIL_TO_PASS tests now pass:
  - `test_prepend_scheme_if_needed[http://user:pass@example.com/path?query-...]` ✅
  - `test_prepend_scheme_if_needed[http://user@example.com/path?query-...]` ✅
- 195 tests passed, 11 skipped
- 8 ERROR tests in unrelated `test_should_bypass_proxies_pass_only_hostname` (pre-existing, not caused by this fix)

**Trajectory**: Convergent success — first iteration resolved.

**Diff**:
```diff
diff --git a/requests/utils.py b/requests/utils.py
index 1c2ae4e0..65405a9f 100644
--- a/requests/utils.py
+++ b/requests/utils.py
@@ -973,6 +973,9 @@ def prepend_scheme_if_needed(url, new_scheme):
     netloc = parsed.netloc
     if not netloc:
         netloc, path = path, netloc
+    if auth:
+        netloc = "%s@%s" % (auth, netloc)
+
 
     if scheme is None:
         scheme = new_scheme
```

## Audit: psf__requests-6028

**Timestamp**: 2026-05-22 - Final verification

### FAIL_TO_PASS
- `test_prepend_scheme_if_needed[http://user:pass@example.com/path?query-http://user:pass@example.com/path?query]` - **PASS** ✅
- `test_prepend_scheme_if_needed[http://user@example.com/path?query-http://user@example.com/path?query]` - **PASS** ✅

### PASS_TO_PASS regressions
**None** - All tests in PASS_TO_PASS contract continue to pass (195 passed, 11 skipped)

### Pre-existing (not counted, confirmed against base capture)
The following 8 tests ERROR due to missing `pytest-mock` fixture - this is a test environment issue unrelated to the code patch:
- `test_should_bypass_proxies_pass_only_hostname[http://172.16.1.1/-172.16.1.1]`
- `test_should_bypass_proxies_pass_only_hostname[http://172.16.1.1:5000/-172.16.1.1]`
- `test_should_bypass_proxies_pass_only_hostname[http://user:pass@172.16.1.1-172.16.1.1]`
- `test_should_bypass_proxies_pass_only_hostname[http://user:pass@172.16.1.1:5000-172.16.1.1]`
- `test_should_bypass_proxies_pass_only_hostname[http://hostname/-hostname]`
- `test_should_bypass_proxies_pass_only_hostname[http://hostname:5000/-hostname]`
- `test_should_bypass_proxies_pass_only_hostname[http://user:pass@hostname-hostname]`
- `test_should_bypass_proxies_pass_only_hostname[http://user:pass@hostname:5000-hostname]`

Error: `fixture 'mocker' not found` - occurs at test setup, before code execution. These tests are NOT in the PASS_TO_PASS contract.

### Summary
The patch successfully resolves the authentication credential loss bug in `prepend_scheme_if_needed` by reconstructing the netloc with auth credentials after extraction. Both FAIL_TO_PASS tests now pass, and zero PASS_TO_PASS tests regressed.

Gate output: 195 passed, 11 skipped, 8 errors (pre-existing fixture issues)
