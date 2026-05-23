# Hypothesis graph: django__django-10973

## H₀: Baseline Failure (abduction)

**Observation:** All 5 tests in `tests/dbshell/test_postgresql.py` fail because they mock `subprocess.run` but the implementation uses `subprocess.check_call`.

**Evidence:**
- Test traceback shows: `File "/testbed/django/db/backends/postgresql/client.py", line 61, in runshell_db` → `subprocess.check_call(args)`
- Test code at line 19 mocks `subprocess.run`: `with mock.patch('subprocess.run', new=_mock_subprocess_run)`
- Tests expect password via `PGPASSWORD` env var (line 20: `self.pgpassword = env.get('PGPASSWORD')`)
- Current implementation uses `.pgpass` file via `PGPASSFILE` env var (client.py:52)

**Classification:** API mismatch - tests expect `subprocess.run` with `env` parameter, implementation uses `subprocess.check_call` with global environment modification.

---

## H₁: Root Cause (deduction - 98%)

**Root cause:** The PostgreSQL client implementation uses the legacy `subprocess.check_call()` API and `.pgpass` file mechanism instead of the modern `subprocess.run()` API with `PGPASSWORD` environment variable.

**Supporting evidence:**
1. `django/db/backends/postgresql/client.py:61` - Uses `subprocess.check_call(args)`
2. `django/db/backends/postgresql/client.py:40-56` - Creates temp `.pgpass` file, requires escaping
3. `django/db/backends/postgresql/client.py:9-13` - `_escape_pgpass()` function only needed for .pgpass format
4. Tests at `tests/dbshell/test_postgresql.py:19-23` - Mock `subprocess.run` with `env` parameter
5. Python 3.6 is in use, `subprocess.run` available since 3.5 ✓

**Why this causes failure:**
- Tests mock `subprocess.run` but implementation calls `subprocess.check_call`
- Mock never intercepts the actual call → execution tries to run real `psql` command
- Real `psql` not in PATH → `FileNotFoundError: [Errno 2] No such file or directory: 'psql'`
- Even if psql existed, password would be in PGPASSFILE not PGPASSWORD

**Confidence:** Deduction - 98% (traced from test mocks through implementation, verified API exists)

---

## Edit Sites

**File:** `django/db/backends/postgresql/client.py`

1. **Lines 9-13** - Remove `_escape_pgpass()` function entirely (no longer needed)

2. **Lines 39-61** - Replace `.pgpass` file mechanism with `subprocess.run()` using `env` parameter:
   - Remove: temp file creation, escaping, PGPASSFILE, UnicodeEncodeError handling
   - Add: Build custom environment dict, set `PGPASSWORD` if password exists
   - Replace: `subprocess.check_call(args)` → `subprocess.run(args, check=True, env=env)`
   - Keep: SIGINT handling (signal.SIG_IGN), cleanup in finally block

**Specific changes:**
- Remove import: `from django.core.files.temp import NamedTemporaryFile` (line 4)
- Remove variable: `temp_pgpass` and all references
- Remove env cleanup: `del os.environ['PGPASSFILE']`
- Add: `env = os.environ.copy()` and `env['PGPASSWORD'] = passwd` logic
- Pass env to subprocess: `subprocess.run(args, check=True, env=env)`

---

## Rejected Hypotheses

None - the mismatch is direct and unambiguous.

---

## Open Questions

None - the fix is straightforward.


## Gate Loop - Iteration 1

**Pre-gate codex volley:** Codex flagged concern about `test_nopass` expecting `env['PGPASSWORD'] = None`, suggesting to set PGPASSWORD unconditionally. However, verification of test mock shows `env.get('PGPASSWORD')` returns `None` when key is absent (not when set to empty string), so conditional `if passwd:` guard is correct.

**Changes applied:**
1. Removed `from django.core.files.temp import NamedTemporaryFile` import
2. Removed `_escape_pgpass()` function entirely
3. Replaced `runshell_db()` implementation:
   - Removed temp `.pgpass` file creation and cleanup
   - Added `env = os.environ.copy()`
   - Added `if passwd: env['PGPASSWORD'] = passwd`
   - Replaced `subprocess.check_call(args)` with `subprocess.run(args, check=True, env=env)`
   - Kept SIGINT handling intact
   - Simplified finally block to only restore SIGINT handler

**Gate result:** ✅ GREEN - All 5 FAIL_TO_PASS tests pass
- test_accent: ok
- test_basic: ok
- test_column: ok
- test_nopass: ok
- test_sigint_handler: ok

**Trajectory:** Convergent success on first iteration.

**Resolution:** Fix confirmed. Django's PostgreSQL client now uses `subprocess.run()` with `PGPASSWORD` environment variable instead of `subprocess.check_call()` with temporary `.pgpass` file.

---

# Audit: django__django-10973

## FAIL_TO_PASS
- test_accent (dbshell.test_postgresql.PostgreSqlDbshellCommandTestCase): PASS ✓
- test_basic (dbshell.test_postgresql.PostgreSqlDbshellCommandTestCase): PASS ✓
- test_column (dbshell.test_postgresql.PostgreSqlDbshellCommandTestCase): PASS ✓
- test_nopass (dbshell.test_postgresql.PostgreSqlDbshellCommandTestCase): PASS ✓
- test_sigint_handler (SIGINT is ignored in Python and passed to psql to abort quries.): PASS ✓

## PASS_TO_PASS regressions
none

## Pre-existing (not counted, confirmed against base capture)
none

## Kill report
Not applicable — all tests pass.

VERDICT: RESOLVED
RE-ENTER: none
