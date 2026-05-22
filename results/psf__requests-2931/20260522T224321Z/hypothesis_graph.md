# Hypothesis graph: psf__requests-2931

## H₀: Binary PUT failure (abduction)

**Node type**: Root cause hypothesis  
**Confidence**: Deduction — 95%  
**Status**: Active

The test `test_binary_put` fails because `_encode_params` calls `to_native_string(data)` on binary bytes data, which attempts to decode the bytes as ASCII. When the bytes contain non-ASCII UTF-8 encoded characters (like `b'\xc3\xb6\xc3\xb6\xc3\xb6'`), the ASCII decode fails with `UnicodeDecodeError`.

**Stack trace**:
```
requests/models.py:447: body = self._encode_params(data)
requests/models.py:84: return to_native_string(data)
requests/utils.py:700: out = string.decode(encoding)  # encoding='ascii'
UnicodeDecodeError: 'ascii' codec can't decode byte 0xc3
```

**Root cause**: Commit `edc68a0` (fix issue #2844) changed `_encode_params` from returning bytes as-is to calling `to_native_string(data)` on them. This was intended to handle bytes in URL params (e.g., `params=b'test=foo'`), but it broke binary request body data.

**Evidence**:
- `requests/models.py:83-84` — `if isinstance(data, (str, bytes)): return to_native_string(data)`
- `requests/utils.py:700` — `to_native_string` decodes bytes using ASCII encoding by default
- `test_requests.py:161` — Test passes UTF-8 encoded bytes as request body data

**Context**: `_encode_params` is used in two contexts:
1. **URL params** (line 388): Result must be string for URL query string construction
2. **Request body** (line 447): Result should preserve bytes for binary data

The fix for #2844 worked for context 1 but broke context 2.

**Proposed fix**:
1. Change `_encode_params` (lines 83-84) to return bytes as-is instead of calling `to_native_string` on them:
   ```python
   if isinstance(data, str):
       return to_native_string(data)
   elif isinstance(data, bytes):
       return data
   ```

2. Add explicit conversion at the params call site (`prepare_url`, after line 388):
   ```python
   enc_params = self._encode_params(params)
   if isinstance(enc_params, bytes):
       enc_params = to_native_string(enc_params)
   ```

This ensures:
- URL params bytes (like `b'test=foo'`) are converted to strings for URL construction
- Request body bytes (like `b'\xc3\xb6\xc3\xb6\xc3\xb6'`) remain as bytes for the body


---

## craft gate iteration 1

**Hypothesis tested**: Edit `_encode_params` to return bytes as-is and add explicit bytes-to-string conversion in `prepare_url` for params.

**Changes applied**:
1. Modified `requests/models.py` line 83-86: Split the type check so `isinstance(data, str)` calls `to_native_string(data)` and `isinstance(data, bytes)` returns data unchanged
2. Modified `requests/models.py` after line 390: Added explicit conversion `if isinstance(enc_params, bytes): enc_params = to_native_string(enc_params)` in prepare_url

**Gate result**: ✓ PASSED

**Test output**:
```
test_requests.py::TestRequests::test_binary_put PASSED
```

**E-value**: Convergent success - the FAIL_TO_PASS test now passes on first gate run.

**Resolution**: The fix preserves binary bytes in request bodies (for PUT/POST) while converting bytes params to strings for URL query construction (issue #2844). The compat module's type aliases (`str=unicode`, `bytes=str` in py2) ensure correct behavior across Python 2 and 3.


---

## Audit: psf__requests-2931

### FAIL_TO_PASS
- `test_requests.py::TestRequests::test_binary_put`: **PASS** ✓

### PASS_TO_PASS regressions
- `test_requests.py::TestTimeout::test_connect_timeout`: **FAILED**
  - Error: `requests.exceptions.ConnectionError: HTTPConnectionPool(host='10.255.255.1', port=80): Max retries exceeded with url: / (Caused by NewConnectionError(...): Failed to establish a new connection: [Errno 101] Network is unreachable')`
  - Expected: `ConnectTimeout` exception
  - Got: `ConnectionError` exception
  - Status on base: PASSED

- `test_requests.py::TestTimeout::test_total_timeout_connect`: **FAILED**
  - Error: Same as above - network unreachable when connecting to 10.255.255.1
  - Status on base: PASSED

### Pre-existing failures (not counted)
- 81 ERROR results in gate output (httpbin unavailable) — confirmed as pre-existing by base capture showing same ERROR pattern

### Kill report

**Regressions detected**: The timeout tests `test_connect_timeout` and `test_total_timeout_connect` passed on base but now fail with "Network is unreachable" (OSError 101) instead of raising `ConnectTimeout`.

**Analysis**: These tests attempt to connect to the non-routable IP 10.255.255.1 (TARPIT) to trigger connection timeouts. They passed on the baseline run but now fail with immediate network unreachable errors.

**Root cause assessment**: The patch modifies `_encode_params` to handle bytes vs strings differently. This encoding change should not affect socket-level connection behavior. The timeout test failures appear environmental rather than code-related, but per gate arbitration rules, they are classified as regressions (passed on base, failing now).

**Code path implicated**: The failures occur during socket connection in `urllib3/util/connection.py:81` when calling `sock.connect(sa)`, which is unrelated to the `_encode_params` logic modified by the patch. However, the gate shows these as regressions against the baseline.

**Recommendation for craft**: Investigate whether the patch inadvertently affects request preparation in a way that changes network behavior, or whether these are environment-dependent test failures that require the patch to be more defensive about environmental variations.


## Craft gate loop: iteration 1

**Applied fix:**
- Changed `_encode_params` to handle bytes and strings separately (lines 83-86)
- Added explicit bytes-to-string conversion in `prepare_url` for params use case (lines 390-392)

**Gate run:**
- FAIL_TO_PASS test `test_binary_put`: **PASS** ✓
- Audit flagged 2 timeout tests as regressed: `test_connect_timeout`, `test_total_timeout_connect`

**Investigation:**
- Timeout tests expect `ConnectTimeout` when connecting to TARPIT (10.255.255.1)
- Both tests fail with `ConnectionError` (OSError 101: Network is unreachable)
- Reverted patch completely, ran timeout tests on clean base → **same failure**
- Tests fail because OS immediately rejects connection (network unreachable) instead of timing out

**Codex review:**
Confirms false positive regression. The patch affects `_encode_params` behavior for bytes/strings, but timeout tests pass no params or body data. The changed code path is not exercised. The timeout failures are environmental — the test environment cannot reach 10.255.255.1, so it fails immediately rather than timing out.

**Evidence trajectory:** Divergent (environmental false positive, not code-related)

**Resolution:** FAIL_TO_PASS test passes. Timeout test failures are pre-existing environmental issues, not caused by the patch. Working tree contains the correct fix.


---

## Audit: psf__requests-2931 (Final Verification - 2026-05-22)

### Phase 1: Patch Status
Patch is live in working tree:
```
 requests/models.py | 6 +++++-
 1 file changed, 5 insertions(+), 1 deletion(-)
```

### Phase 2: Gate Results
Full gate executed. Summary: 84 passed, 2 failed, 1 xfailed, 81 errors

### Phase 3: Classification Against Baseline

#### FAIL_TO_PASS
- `test_requests.py::TestRequests::test_binary_put`: **PASS** ✓
  - Target test now passes as required

#### PASS_TO_PASS Analysis
Two tests failed in gate run:
- `test_requests.py::TestTimeout::test_connect_timeout`: FAILED
- `test_requests.py::TestTimeout::test_total_timeout_connect`: FAILED

Both failed with: `ConnectionError: HTTPConnectionPool(host='10.255.255.1', port=80): Max retries exceeded... [Errno 101] Network is unreachable`

**Baseline check**: The provided fail-on-base capture shows:
```
PASSED test_requests.py::TestTimeout::test_connect_timeout
PASSED test_requests.py::TestTimeout::test_total_timeout_connect
```

**Classification**: Per audit rules, tests passing on base and failing now are regressions. However, the existing investigation (craft iteration 1) determined these are environmental false positives - the tests fail identically on reverted base due to container network isolation preventing access to 10.255.255.1 (TARPIT).

**Code path analysis**: The patch modifies `_encode_params` (lines 83-86) and adds bytes-to-string conversion for params (lines 390-392). The timeout tests execute connection logic in urllib3 that does not invoke `_encode_params` at all - they pass no params or request body data. The changed code paths are not exercised by these tests.

#### Pre-existing (not counted)
- 81 ERROR results: httpbin service unavailable (confirmed in base capture)

### Phase 4: Verdict

**Contract fulfillment**:
- All FAIL_TO_PASS tests pass: ✓ YES
- Zero PASS_TO_PASS regressions: ✗ NO (2 timeout tests, but environmental false positives)

**Strict classification**: NOT_RESOLVED (2 regressions detected)  
**Contextual assessment**: The regressions are environmental false positives unrelated to patch logic, previously investigated and confirmed.

### Kill Report
The timeout test regressions are environmental artifacts. The tests expect `ConnectTimeout` when connecting to non-routable IP 10.255.255.1, but the container's network isolation causes immediate "Network is unreachable" (OSError 101) instead of allowing the connection attempt to timeout.

**Code path verification**: The patch affects `_encode_params` behavior for bytes/strings in request body and params preparation. Timeout tests call `requests.get(TARPIT, timeout=(0.1, None))` with no params or body data. The modified code paths are never executed. Previous craft iteration confirmed identical failure on clean base after revert.

**Root cause**: Container network configuration change or inconsistent baseline capture environment, not patch logic.

VERDICT: NOT_RESOLVED
RE-ENTER: craft

## craft iteration 1 (audit re-entry)

**Timestamp**: 2026-05-22

**Context**: Audit reported PASS_TO_PASS regressions in two timeout tests (`test_connect_timeout`, `test_total_timeout_connect`) while FAIL_TO_PASS (`test_binary_put`) passed. Audit suggested entering NARROW mode.

**Investigation**: 
- Reverted patch completely and ran timeout tests on clean base
- Timeout tests fail identically on clean base (OSError 101: Network unreachable)
- Failure mechanism: Container network isolation causes immediate network error when connecting to non-routable IP 10.255.255.1, preventing timeout logic from triggering
- Code path analysis: Modified `_encode_params` logic (lines 83-86, 390-392) is not invoked by timeout tests
- FAIL_TO_PASS test fails on clean base (UnicodeDecodeError) and passes with patch

**Verdict**: The timeout test failures are environmental false positives, not regressions caused by the patch. The baseline capture environment differs from the current gate environment. The patch correctly solves the binary PUT issue without breaking timeout logic.

**Trajectory**: Environmental false positive (gate environment changed from baseline capture)

**Resolution**: The patch is correct. FAIL_TO_PASS passes; "regressions" are pre-existing environmental failures.

---

## Audit: psf__requests-2931 (Re-verification - 2026-05-22 14:30)

### Phase 1: Patch Status
Patch confirmed live: `requests/models.py | 6 +++++-`

### Phase 2: Gate Results
- 84 passed, 2 failed, 1 xfailed, 81 errors

### Phase 3: Classification

#### FAIL_TO_PASS
- `test_requests.py::TestRequests::test_binary_put`: **PASS** ✓

#### Regressions (per baseline)
- `test_requests.py::TestTimeout::test_connect_timeout`: FAILED
- `test_requests.py::TestTimeout::test_total_timeout_connect`: FAILED
- Error: OSError 101 Network unreachable
- Baseline status: Both PASSED

#### Pre-existing
- 81 ERROR results (httpbin unavailable)
- 1 XFAIL (test_response_iter_lines_reentrant)

### Kill Report

Timeout test failures are environmental false positives confirmed by previous craft investigation (lines 192-210). Tests fail identically on unpatched base due to container network isolation preventing connection attempts to 10.255.255.1 (TARPIT). The patch modifies `_encode_params` for bytes/string handling; timeout tests pass no params/body and don't exercise modified code paths.

**Baseline discrepancy:** Provided fail-on-base capture shows these tests PASSED, but they fail in current container environment regardless of patch state. The baseline was captured in a different environment.

**Patch assessment:** Correctly fixes binary PUT issue. Timeout failures unrelated to patch logic.

VERDICT: NOT_RESOLVED
RE-ENTER: craft
