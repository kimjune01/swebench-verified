# Hypothesis graph: django__django-16502

## H₀: Missing HEAD request body stripping (abduction, 90%)

**Date**: 2026-05-23
**Mode**: Abduction
**Confidence**: 90%

### Symptom
Test `test_no_body_returned_for_head_requests` fails because HEAD requests return the full response body when they should return no body (just `b"\r\n"`). Also, Content-Length header is present when it should be absent.

### Evidence
1. **Test failure**: AssertionError: `b'<!DOCTYPE html><html><body>Hello World</body></html>' != b'\r\n'`
2. **Git history** (commit bb0b4b705b): In #26052, Django removed `conditional_content_removal()` function that stripped response bodies for HEAD requests. The commit message assumed "common servers (gunicorn, mod_wsgi etc) already do so."
3. **Standard library verification**: Tested `wsgiref.simple_server.WSGIRequestHandler` directly - it ALSO returns body for HEAD requests. The assumption that wsgiref handles HEAD stripping was incorrect.
4. **Code inspection**: Django's `ServerHandler` in `django/core/servers/basehttp.py` does not override any methods to handle HEAD requests specially.

### Root cause
Django's `ServerHandler` class (lines 119-147 in django/core/servers/basehttp.py) extends `simple_server.ServerHandler` but doesn't implement HEAD request handling. When a HEAD request is processed:
1. WSGI app returns full body
2. `BaseHandler.finish_response()` iterates result and calls `write()` for each chunk  
3. `write()` calls `_write()` which sends data to client
4. `cleanup_headers()` sets Content-Length based on bytes_sent

Neither the body stripping nor Content-Length removal happens.

### Edit sites
File: `django/core/servers/basehttp.py`, class `ServerHandler` (lines 119-147)

**Site 1**: Override `_write()` method to check `self.environ.get('REQUEST_METHOD') == 'HEAD'` and skip writing body data for HEAD requests.

**Site 2**: Modify `cleanup_headers()` method to remove Content-Length header for HEAD requests after calling `super().cleanup_headers()`.

### Supporting code
**Line 119-147**: Current ServerHandler class with no HEAD handling
```python
class ServerHandler(simple_server.ServerHandler):
    http_version = "1.1"

    def __init__(self, stdin, stdout, stderr, environ, **kwargs):
        # ... LimitedStream setup ...

    def cleanup_headers(self):
        super().cleanup_headers()
        # HTTP/1.1 connection handling, but no HEAD check
        if "Content-Length" not in self.headers:
            self.headers["Connection"] = "close"
        # ...

    def close(self):
        self.get_stdin().read()
        super().close()
```

**Deleted code** (commit bb0b4b705b, django/http/utils.py):
```python
def conditional_content_removal(request, response):
    # ...
    if request.method == 'HEAD':
        if response.streaming:
            response.streaming_content = []
        else:
            response.content = b''
    return response
```

This was the old HEAD stripping logic that needs to be reimplemented at the WSGI handler level.


## Craft: Gate Loop

### Iteration 1 - Initial draft with _write() override
**Hypothesis**: Override `_write()` to prevent body transmission for HEAD requests.
**Result**: DIVERGENT - codex caught that `_write()` is used for headers too (status line, Date, Server). Blocking _write() would suppress the entire HTTP response, not just the body.
**Evidence**: codex review showed `send_preamble()` and `send_headers()` both call `_write()`.

### Iteration 2 - Revised to override write() instead
**Hypothesis**: Override `write()` to allow headers but skip body for HEAD requests.
**Result**: DIVERGENT - Gate failed with `AttributeError: 'Headers' object has no attribute 'pop'`.
**Evidence**: `self.headers.pop("Content-Length", None)` fails because wsgiref Headers is not a full dict.
**Fix**: Changed to use `del self.headers["Content-Length"]` after checking existence.

### Iteration 3 - Fixed Headers API
**Hypothesis**: Use `del self.headers["Content-Length"]` instead of `.pop()`.
**Result**: DIVERGENT - Test passed for body removal but failed on Connection: close header.
**Evidence**: Gate output showed `b'Connection: close\r\n'` in response. Removing Content-Length triggered Django logic to add Connection: close for unknown-length responses.

### Iteration 4 - Exclude HEAD from Connection: close logic
**Hypothesis**: HEAD responses don't need Content-Length for connection framing, so exclude them from the "add Connection: close when no Content-Length" logic.
**Result**: CONVERGENT - All tests pass!
**Evidence**: Gate output shows `OK` for all 5 tests including `test_no_body_returned_for_head_requests`.

**Final implementation**:
1. Override `write()` to send headers with `bytes_sent = 0` for HEAD, then return early without writing body data
2. In `cleanup_headers()`, remove Content-Length for HEAD requests
3. Exclude HEAD from both "Connection: close" conditions (missing Content-Length and non-threading server)

The fix correctly handles RFC compliance: HEAD responses return status + headers but no body, and persistent connections work without Content-Length because there's no body to frame.


## Audit: django__django-16502

**Date**: 2026-05-22
**Gate run**: PASS (5/5 tests)

### FAIL_TO_PASS
- `test_no_body_returned_for_head_requests`: **PASS** ✓ (was failing on base with AssertionError, now passes)

### PASS_TO_PASS
- `test_https`: **PASS** ✓
- `test_log_message`: **PASS** ✓
- `test_strips_underscore_headers`: **PASS** ✓
- `test_broken_pipe_errors`: **PASS** ✓

### Regressions
None

### Pre-existing failures (confirmed against base capture)
None - the single FAIL_TO_PASS test now passes.

### Classification
All FAIL_TO_PASS tests pass. Zero PASS_TO_PASS regressions. The craft patch correctly implements HEAD request handling by:
1. Overriding `write()` to prevent body transmission for HEAD requests
2. Removing Content-Length header for HEAD responses
3. Excluding HEAD from Connection: close logic (no Content-Length needed since no body to frame)

The fix is complete and introduces no regressions.
