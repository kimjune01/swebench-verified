# Hypothesis graph: psf__requests-5414

## Hypothesis H0 (abduction)
**Status**: Current hypothesis
**Mode**: Abduction (from code reading and tracing)
**Confidence**: 90%

### Symptom
Test `test_invalid_url[InvalidURL-http://.example.com]` fails because `requests.get("http://.example.com")` raises `urllib3.exceptions.LocationParseError` instead of `requests.exceptions.InvalidURL`.

### Root Cause
The hostname `.example.com` has an invalid label (empty label caused by leading dot), but this is not detected during URL preparation in `requests/models.py:prepare_url()`.

The validation flow in `prepare_url` (lines 400-407):
1. Only runs IDNA encoding validation if `not unicode_is_ascii(host)` (non-ASCII)
2. For ASCII hosts, only checks if `host.startswith(u'*')`
3. `.example.com` is ASCII and doesn't start with `*`, so it passes through
4. Later, when urllib3 tries to create a connection, it raises `LocationParseError: "label empty or too long"`
5. This exception is not caught in `requests/adapters.py:send()`, so it propagates to the caller

### Evidence
- `requests/models.py:401-407`: Only non-ASCII hosts go through IDNA encoding which would catch invalid labels
- `requests/adapters.py:500-540`: Exception handlers don't catch `LocationParseError`/`LocationValueError`
- Manual test: IDNA encoding `.example.com` raises `idna.core.IDNAError: Empty Label`
- Manual test: `requests.get("http://*example.com")` correctly raises `InvalidURL` (caught by explicit check)

### Edit Sites
**Option 1** (Preferred): Add exception handler in `requests/adapters.py`
- Location: After line 415 (existing `LocationValueError` catch) or in the exception handler chain starting at line 500
- Action: Catch `LocationValueError` (parent of `LocationParseError`) during `conn.urlopen()` and convert to `InvalidURL`

**Option 2** (Alternative): Extend validation in `requests/models.py`
- Location: Line 400-407 in `prepare_url()`
- Action: Run IDNA encoding on ALL hosts (not just non-ASCII), OR add explicit check for `.startswith('.')`

### Why Option 1 is preferred
- LocationValueError is already imported in adapters.py
- Catches ALL invalid hosts that urllib3 might reject, not just those starting with `.`
- Mirrors the existing pattern at line 413-415 which catches LocationValueError from `get_connection()`
- More defensive: catches other URL parse errors that might occur during connection


## Craft gate loop - iteration 1

**Action**: Added `LocationValueError` exception handler in `requests/adapters.py` after line 499, catching exceptions from `conn.urlopen()` and converting to `InvalidURL(e, request=request)`. This mirrors the existing pattern at lines 413-415 where `LocationValueError` is caught after `get_connection()`.

**Applied diff**:
```diff
--- a/requests/adapters.py
+++ b/requests/adapters.py
@@ -499,6 +499,8 @@ class HTTPAdapter(BaseAdapter):
                     low_conn.close()
                     raise

+        except LocationValueError as e:
+            raise InvalidURL(e, request=request)
         except (ProtocolError, socket.error) as err:
             raise ConnectionError(err, request=request)
```

**Gate result**: FAIL_TO_PASS test PASSED
- `tests/test_requests.py::TestRequests::test_invalid_url[InvalidURL-http://.example.com]` PASSED

**Gate trajectory**: Convergent (success) — the FAIL_TO_PASS test now passes. Gate also shows 127 other tests passing. The 4 failures and 158 errors are test infrastructure issues (network unreachable, pytest fixture recursion) unrelated to this patch.

**Codex review**: "The patch is narrowly scoped and matches the failing behavior: `urllib3` raises `LocationValueError` for malformed host values, and `requests` should surface that as `InvalidURL`. The target test passing confirms the intended exception translation works for `http://.example.com`."

**Verdict**: RESOLVED — FAIL_TO_PASS test passes, fix is minimal and follows existing exception handling pattern.

## Audit: psf__requests-5414

### Phase 1: Patch verification
Patch is live in working tree:
```
 requests/adapters.py | 3 +++
 1 file changed, 3 insertions(+)
```

The patch adds a `LocationValueError` exception handler in the second try-except block (around `conn.urlopen()`), converting to `InvalidURL`.

### Phase 2: Gate execution
Ran full test suite via `/tmp/gate-psf_requests-5414`:
- 127 tests PASSED
- 4 tests FAILED  
- 1 test XFAILED
- 158 tests ERROR

### Phase 3: Classification

#### FAIL_TO_PASS
- `tests/test_requests.py::TestRequests::test_invalid_url[InvalidURL-http://.example.com]`: **PASSED** ✓

#### PASS_TO_PASS regressions
None. The 4 FAILED tests are:
- `tests/test_requests.py::TestTimeout::test_connect_timeout[timeout0]`
- `tests/test_requests.py::TestTimeout::test_connect_timeout[timeout1]`
- `tests/test_requests.py::TestTimeout::test_total_timeout_connect[timeout0]`
- `tests/test_requests.py::TestTimeout::test_total_timeout_connect[timeout1]`

These timeout tests are failing with `OSError: [Errno 101] Network is unreachable` when attempting to connect to `10.255.255.1:80`. This is an environmental/infrastructure issue in the Docker container, not a code regression.

**Analysis of patch impact**: The patch adds a `LocationValueError` handler that executes BEFORE the existing `MaxRetryError` handler. The timeout tests fail with `MaxRetryError` wrapping `NewConnectionError` wrapping `OSError`, which flows through the `MaxRetryError` handler (line ~520) and becomes `ConnectionError`. Our `LocationValueError` handler cannot intercept this path since `MaxRetryError` and `LocationValueError` are independent exception types.

**Conclusion**: These 4 failures are pre-existing environmental issues, not regressions introduced by the patch.

#### Pre-existing (not counted, confirmed against base capture)
All 158 ERROR tests match the fail-on-base capture pattern (imports failing, network tests erroring, etc.). These were already broken before the patch.

### Phase 4: Verdict

**Contract satisfied**:
- ✓ All FAIL_TO_PASS tests pass (1/1)  
- ✓ Zero PASS_TO_PASS regressions
- ✓ Patch is minimal, narrowly scoped, follows existing patterns

The 4 timeout test failures are environmental (network unreachable in container) and cannot be caused by our LocationValueError exception handler, which operates on a different exception type and code path.

VERDICT: RESOLVED
RE-ENTER: none
