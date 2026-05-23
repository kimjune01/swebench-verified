# Hypothesis graph: psf__requests-1142

## H₀: GET requests set Content-Length unconditionally (ABDUCTION)

**Timestamp**: 2026-05-22 (initial recon)

**Observation**: Test `test_no_content_length` fails because prepared GET/HEAD requests contain `Content-Length: 0` header when they shouldn't have any Content-Length header.

**Hypothesis**: The `prepare_content_length()` method in `requests/models.py:389` unconditionally sets `self.headers['Content-Length'] = '0'` as its first action, regardless of whether there's a body or what HTTP method is being used.

**Evidence**:
- `requests/models.py:389` — Always executes `self.headers['Content-Length'] = '0'`
- `requests/models.py:394-395` — Only updates Content-Length if `body is not None`
- For GET requests with no data, `body=None`, so the header remains '0'
- Confirmed via test: `requests.Request('GET', url).prepare()` has `Content-Length: 0` in headers

**Call path**:
1. `Request.prepare()` (line 216) creates PreparedRequest
2. `PreparedRequest.prepare_body(data=None, files=None)` (line 332)
3. `PreparedRequest.prepare_content_length(body=None)` (line 388)
4. Line 389 sets Content-Length to '0'
5. Line 394 condition `elif body is not None:` is False
6. Content-Length remains '0'

**Root cause**: Line 389 unconditionally sets Content-Length, treating None body and empty body the same. HTTP semantics: GET/HEAD requests without a body should not have Content-Length header.

**Confidence**: deduction — 95% (traced through code, reproduced behavior, found exact line)

**Fix**: Remove the unconditional assignment at line 389. Only set Content-Length when there's actually a body to send.

**Git history**: Introduced in commit f003025 ("Attach Content-Length to everything. Closes #223"), refactored into separate method in commit 628e393b.


## Gate Loop - Iteration 1

**Draft:** Modified `prepare_content_length()` in `requests/models.py` to only set `Content-Length: 0` for non-GET/HEAD methods when body is None. GET and HEAD requests with no body now have no Content-Length header.

**Codex volley:** Approved the method-specific approach. Confirmed that POST/PUT/PATCH/DELETE should still get `Content-Length: 0` with no body, while GET/HEAD should omit it entirely.

**Applied fix:**
```python
def prepare_content_length(self, body):
    if hasattr(body, 'seek') and hasattr(body, 'tell'):
        body.seek(0, 2)
        self.headers['Content-Length'] = str(body.tell())
        body.seek(0, 0)
    elif body is not None:
        self.headers['Content-Length'] = str(len(body))
    elif self.method not in ('GET', 'HEAD') and self.headers.get('Content-Length') is None:
        self.headers['Content-Length'] = '0'
```

**Gate result:** ✅ PASS
- `test_no_content_length` now passes
- Other test failures are unrelated (urllib3 'strict' parameter compatibility issue)

**Trajectory:** Convergent-success on first iteration


## Audit: psf__requests-1142

**Timestamp**: 2026-05-22 (verification phase)

### FAIL_TO_PASS
- test_requests.py::RequestsTestCase::test_no_content_length: **PASS** ✓

### PASS_TO_PASS regressions
None — all 5 PASS_TO_PASS tests remain passing:
- test_basic_building: PASS ✓
- test_entry_points: PASS ✓
- test_invalid_url: PASS ✓
- test_params_are_added_before_fragment: PASS ✓
- test_path_is_not_double_encoded: PASS ✓

### Pre-existing failures (not counted, confirmed against base capture)
All 21 other test failures exhibit the same `TypeError: __init__() got an unexpected keyword argument 'strict'` error from `requests/packages/urllib3/connectionpool.py:196` that was present in the fail-on-base capture. These failures are unrelated to the Content-Length fix:
- test_BASICAUTH_TUPLE_HTTP_200_OK_GET
- test_DIGESTAUTH_WRONG_HTTP_401_GET
- test_DIGEST_HTTP_200_OK_GET
- test_HTTP_200_OK_GET_ALTERNATIVE
- test_HTTP_200_OK_GET_WITH_MIXED_PARAMS
- test_HTTP_200_OK_GET_WITH_PARAMS
- test_HTTP_200_OK_HEAD
- test_HTTP_200_OK_PUT
- test_HTTP_302_ALLOW_REDIRECT_GET
- test_POSTBIN_GET_POST_FILES
- test_POSTBIN_GET_POST_FILES_WITH_DATA
- test_custom_content_type
- test_decompress_gzip
- test_different_encodings_dont_break_post
- test_links
- test_prepared_request_hook
- test_request_ok_set
- test_status_raising
- test_unicode_get
- test_urlencoded_get_query_multivalued_param
- test_user_agent_transfers

These all fail because urllib3's bundled connectionpool is passing a `strict` parameter to Python 3.x's HTTPConnection, which no longer accepts it. This is an environment/compatibility issue, not a regression from the Content-Length fix.

### Patch verification
The craft patch is live in the tree:
```diff
diff --git a/requests/models.py b/requests/models.py
@@ -386,13 +386,14 @@ class PreparedRequest(RequestEncodingMixin, RequestHooksMixin):
         self.body = body
 
     def prepare_content_length(self, body):
-        self.headers['Content-Length'] = '0'
         if hasattr(body, 'seek') and hasattr(body, 'tell'):
             body.seek(0, 2)
             self.headers['Content-Length'] = str(body.tell())
             body.seek(0, 0)
         elif body is not None:
             self.headers['Content-Length'] = str(len(body))
+        elif self.method not in ('GET', 'HEAD') and self.headers.get('Content-Length') is None:
+            self.headers['Content-Length'] = '0'
```

The fix correctly:
1. Removed the unconditional Content-Length='0' assignment
2. Only sets Content-Length='0' for non-GET/HEAD methods when body is None
3. Preserves existing Content-Length headers when already set
4. Allows file-like bodies and non-None bodies to set appropriate lengths

VERDICT: RESOLVED
RE-ENTER: none

