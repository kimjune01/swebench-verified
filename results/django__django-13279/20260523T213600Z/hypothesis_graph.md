# Hypothesis graph: django__django-13279

## H1: encode() always uses new format, breaking legacy decode compatibility
**Type:** Abduction  
**Confidence:** 95% (deduction from code reading and git history)

**Observation:**
Tests fail with `binascii.Error: Incorrect padding` when calling `_legacy_decode()` on data produced by `encode()` with `DEFAULT_HASHING_ALGORITHM='sha1'`.

**Stack trace:**
```
tests/sessions_tests/tests.py:333 in test_default_hashing_algorith_legacy_decode
    self.assertEqual(self.session._legacy_decode(encoded), data)
django/contrib/sessions/backends/base.py:126 in _legacy_decode
    encoded_data = base64.b64decode(session_data.encode('ascii'))
binascii.Error: Incorrect padding
```

**Root cause:**
In commit d4fff711d4 (Fixed #31274), `encode()` was changed from:
```python
# OLD (legacy format):
serialized = self.serializer().dumps(session_dict)
hash = self._hash(serialized)
return base64.b64encode(hash.encode() + b":" + serialized).decode('ascii')
```

To:
```python
# NEW (signing infrastructure format):
return signing.dumps(
    session_dict, salt=self.key_salt, serializer=self.serializer,
    compress=True,
)
```

The `encode()` method doesn't check `settings.DEFAULT_HASHING_ALGORITHM`, so it always uses the new format. But `_legacy_decode()` expects base64-encoded `hash:serialized` format. The new signing format is incompatible with base64 decoding, causing the padding error.

**Evidence:**
- `django/contrib/sessions/backends/base.py:109-114` - encode() uses signing.dumps() unconditionally
- `django/contrib/sessions/backends/base.py:126` - _legacy_decode() expects base64 format
- Problem statement: "setting DEFAULT_HASHING_ALGORITHM to 'sha1' is not enough to support running multiple instances"
- Problem statement suggests: "We could use the legacy encode() when DEFAULT_HASHING_ALGORITHM == 'sha1'"

**Solution:**
Modify `encode()` to check `settings.DEFAULT_HASHING_ALGORITHM`:
- If 'sha1': use legacy format (base64 encoding of hash:serialized)
- If 'sha256': use new format (signing.dumps)

**Edit sites:**
- `django/contrib/sessions/backends/base.py` lines 109-114 (encode method)

## Craft gate loop

### Iteration 1: Draft + volley + apply

**Hypothesis**: When `DEFAULT_HASHING_ALGORITHM='sha1'`, `encode()` should produce legacy format `base64(hash:serialized)` instead of the new `signing.dumps()` format.

**Edit**: Modified `django/contrib/sessions/backends/base.py:109-119` to check `settings.DEFAULT_HASHING_ALGORITHM`. When it equals 'sha1', use legacy encoding: serialize with `serializer().dumps()`, compute hash with `_hash()`, return `base64.b64encode(session_hash.encode() + b":" + serialized).decode('ascii')`. Otherwise use existing `signing.dumps()`.

**Codex pre-gate review**: Functionally correct. Minor fix: renamed `hash` → `session_hash` to avoid shadowing built-in.

**Gate result**: ✅ PASS
- All 384 tests pass
- All 9 FAIL_TO_PASS variants of `test_default_hashing_algorith_legacy_decode` now pass
- No regressions

**Trajectory**: Convergent success — first gate attempt passed.

**Resolution**: RESOLVED — FAIL_TO_PASS tests pass, no PASS_TO_PASS regressions.

---

# Audit: django__django-13279

## Patch verification

Patch is live:
```
 django/contrib/sessions/backends/base.py | 5 +++++
 1 file changed, 5 insertions(+)
```

Applied diff:
```python
def encode(self, session_dict):
    "Return the given session dictionary serialized and encoded as a string."
+   # RemovedInDjango40Warning: pre-Django 3.1 format will be invalid.
+   if getattr(settings, 'DEFAULT_HASHING_ALGORITHM', 'sha256') == 'sha1':
+       serialized = self.serializer().dumps(session_dict)
+       session_hash = self._hash(serialized)
+       return base64.b64encode(session_hash.encode() + b":" + serialized).decode('ascii')
    return signing.dumps(
        session_dict, salt=self.key_salt, serializer=self.serializer,
        compress=True,
```

## FAIL_TO_PASS results

All 7 FAIL_TO_PASS tests now **PASS**:

- `test_default_hashing_algorith_legacy_decode (sessions_tests.tests.CookieSessionTests)`: **PASS**
- `test_default_hashing_algorith_legacy_decode (sessions_tests.tests.CacheSessionTests)`: **PASS**
- `test_default_hashing_algorith_legacy_decode (sessions_tests.tests.FileSessionTests)`: **PASS**
- `test_default_hashing_algorith_legacy_decode (sessions_tests.tests.FileSessionPathLibTests)`: **PASS**
- `test_default_hashing_algorith_legacy_decode (sessions_tests.tests.CacheDBSessionTests)`: **PASS**
- `test_default_hashing_algorith_legacy_decode (sessions_tests.tests.CacheDBSessionWithTimeZoneTests)`: **PASS**
- `test_default_hashing_algorith_legacy_decode (sessions_tests.tests.DatabaseSessionTests)`: **PASS**

## PASS_TO_PASS regressions

**None.** Full gate ran 384 tests with status: `OK (skipped=2, expected failures=1)`

## Pre-existing failures (not counted)

**None.** No failures in current gate run.

## Baseline comparison

Fail-on-base capture showed these tests failing before the patch:
- `CookieSessionTests.test_default_hashing_algorith_legacy_decode`: `binascii.Error: Incorrect padding`
- `FileSessionPathLibTests.test_default_hashing_algorith_legacy_decode`: `binascii.Error: Incorrect padding`
- `FileSessionTests.test_default_hashing_algorith_legacy_decode`: `binascii.Error: Incorrect padding`
- `CacheDBSessionTests.test_default_hashing_algorith_legacy_decode`: `AssertionError: {} != {'a test key': 'a test value'}`

After the patch, all these tests now pass. The fix successfully resolved the incompatibility between `encode()` and `_legacy_decode()` when `DEFAULT_HASHING_ALGORITHM='sha1'`.

VERDICT: RESOLVED
RE-ENTER: none
