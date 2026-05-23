# Hypothesis graph: django__django-13809

## H₀: Initial diagnosis (deduction)

**Symptom**: Test `test_skip_checks` fails with `TypeError: Unknown option(s) for runserver command: skip_checks.`

**Root cause**: The runserver command doesn't support the `--skip-checks` option because:
1. `requires_system_checks = []` (empty list, falsy) prevents BaseCommand from auto-adding the `--skip-checks` argument
2. The command doesn't manually add `--skip-checks` in its `add_arguments` method
3. The `inner_run` method unconditionally performs system checks (lines 117-118)

**Evidence**:
- `django/core/management/commands/runserver.py:28` — `requires_system_checks = []`
- `django/core/management/commands/runserver.py:38-52` — `add_arguments` method has no `--skip-checks`
- `django/core/management/commands/runserver.py:117-118` — unconditional check execution
- `django/core/management/base.py:316-319` — BaseCommand only adds `--skip-checks` if `requires_system_checks` is truthy
- `django/core/management/commands/migrate.py:23-25` — reference implementation of `--skip-checks`

**Confidence**: deduction — 99%

**Edit sites**:
1. `django/core/management/commands/runserver.py` lines 38-52: Add `--skip-checks` argument in `add_arguments` method
2. `django/core/management/commands/runserver.py` lines 117-121: Wrap system check execution in conditional based on `options.get('skip_checks', False)`


## craft Gate Loop

### Iteration 1: Initial fix

**Diff applied:**
- Added `--skip-checks` argument to `add_arguments` method (action='store_true')
- Wrapped "Performing system checks..." print and `self.check(display_num_errors=True)` in conditional: `if not options.get('skip_checks', False):`

**codex pre-gate review:** No functional issues. Addresses all three root causes. Noted that `check_migrations()` still runs (correct behavior — skip system checks, not migration checks).

**Gate result:** ✅ PASS
- All 276 tests passed (20 skipped)
- FAIL_TO_PASS test `test_skip_checks (admin_scripts.tests.ManageRunserver)` now passing

**Resolution:** RESOLVED in 1 iteration

## Audit: django__django-13809

### Phase 1: Patch confirmation
Patch is live in container:
- `django/core/management/commands/runserver.py` modified (7 insertions, 2 deletions)
- Added `--skip-checks` argument to parser
- Wrapped system check execution in conditional

### Phase 2: Gate execution
Full gate ran 276 tests in 32.319s - **ALL PASSED** (20 skipped - Watchman unavailable)

### Phase 3: Classification

#### FAIL_TO_PASS
- **test_skip_checks (admin_scripts.tests.ManageRunserver)**: ✅ **PASS**
  - Previously failed with: `TypeError: Unknown option(s) for runserver command: skip_checks`
  - Now passes - the `--skip-checks` option is recognized and functional

#### PASS_TO_PASS regressions
**None detected.** All 276 tests passed, including all specified PASS_TO_PASS tests:
- test_common_roots (utils_tests.test_autoreload.TestCommonRoots) - ok
- test_no_exception (utils_tests.test_autoreload.TestRaiseLastException) - ok
- test_raises_custom_exception (utils_tests.test_autoreload.TestRaiseLastException) - ok
- test_raises_exception (utils_tests.test_autoreload.TestRaiseLastException) - ok
- test_raises_exception_with_context (utils_tests.test_autoreload.TestRaiseLastException) - ok
- test_watchman_available (utils_tests.test_autoreload.GetReloaderTests) - ok
- test_watchman_unavailable (utils_tests.test_autoreload.GetReloaderTests) - ok
- test_sys_paths_absolute (utils_tests.test_autoreload.TestSysPathDirectories) - ok
- test_sys_paths_directories (utils_tests.test_autoreload.TestSysPathDirectories) - ok
- test_sys_paths_non_existing (utils_tests.test_autoreload.TestSysPathDirectories) - ok
- All other tests from the full suite (admin_scripts.tests.StartProject, utils_tests.test_autoreload.*) - ok

#### Pre-existing failures
**None.** The fail-on-base capture showed tests running without failures before truncation. The current gate shows zero failures.

### Phase 4: Verdict

✅ **All FAIL_TO_PASS tests now pass**
✅ **Zero PASS_TO_PASS regressions**
✅ **Contract fully satisfied**

VERDICT: RESOLVED
RE-ENTER: none
