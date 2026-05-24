# Hypothesis graph: django__django-11239

## H₀: Initial abduction
**Timestamp**: 2026-05-23 (recon phase)
**Type**: Abduction
**Status**: Active

The test `test_ssl_certificate` fails because the PostgreSQL `DatabaseClient.runshell_db()` method does not set environment variables for SSL parameters (`sslmode`, `sslrootcert`, `sslcert`, `sslkey`), even though these parameters are passed in `conn_params`.

**Evidence**:
- Test expects: `{'PGSSLCERT': 'client.crt', 'PGSSLKEY': 'client.key', 'PGSSLMODE': 'verify-ca', 'PGSSLROOTCERT': 'root.crt'}`
- Test receives: `{}`
- Error message: "First differing element 1: {} != {'PGSSLCERT': 'client.crt', ...}"

**Call path**:
1. Test calls `DatabaseClient.runshell_db(dbinfo)` with SSL params
2. `runshell_db` at django/db/backends/postgresql/client.py:12
3. Only `PGPASSWORD` is set (line 32), SSL env vars are never set
4. subprocess.run() is called with incomplete environment

**Root cause**:
Lines 31-32 of django/db/backends/postgresql/client.py only handle the `password` parameter by setting `PGPASSWORD`. The SSL parameters (`sslmode`, `sslrootcert`, `sslcert`, `sslkey`) are not extracted from `conn_params` and their corresponding environment variables (`PGSSLMODE`, `PGSSLROOTCERT`, `PGSSLCERT`, `PGSSLKEY`) are never set in `subprocess_env`.

**Confidence**: Deduction — 99%
The code path is explicit, the test expectations are clear, and the missing logic is directly observable.


## Craft gate loop — django__django-11239

### Iteration 1: Initial fix

**Hypothesis**: The `DatabaseClient.runshell_db()` method needs to extract SSL parameters (`sslmode`, `sslrootcert`, `sslcert`, `sslkey`) from `conn_params` and set corresponding environment variables (`PGSSLMODE`, `PGSSLROOTCERT`, `PGSSLCERT`, `PGSSLKEY`) following the same pattern as `PGPASSWORD`.

**Change applied**:
- Added extraction of SSL parameters after the `passwd` extraction (lines 20-23)
- Added conditional setting of SSL environment variables after `PGPASSWORD` (lines 37-44)

**Codex review**: "patch is narrowly correct. Main missing piece is the test" (but test already exists in repo)

**Gate result**: ✅ PASS — all 6 tests pass, including `test_ssl_certificate`

**E-value**: Convergent success (green on first iteration)

**Resolution**: RESOLVED — FAIL_TO_PASS test now passes without breaking existing tests.

---

# Audit: django__django-11239

## FAIL_TO_PASS
- test_ssl_certificate (dbshell.test_postgresql.PostgreSqlDbshellCommandTestCase): PASS ✓

## PASS_TO_PASS regressions
none

## Pre-existing (not counted, confirmed against base capture)
none

## Gate output
All 6 tests passed successfully:
- test_accent: ok
- test_basic: ok
- test_column: ok
- test_nopass: ok
- test_sigint_handler: ok
- test_ssl_certificate: ok

The patch successfully added SSL environment variable handling to `django/db/backends/postgresql/client.py`, setting PGSSLMODE, PGSSLCERT, PGSSLKEY, and PGSSLROOTCERT from OPTIONS when present.

VERDICT: RESOLVED
RE-ENTER: none
