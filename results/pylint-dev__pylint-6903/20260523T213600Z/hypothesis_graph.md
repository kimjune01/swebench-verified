# Hypothesis graph: pylint-dev__pylint-6903

## H₀ (abduction): Initial failure observation
**Status:** CONFIRMED
**Mode:** Deduction (traced through code)
**Confidence:** 99%

The test `test_pylint_run_jobs_equal_zero_dont_crash_with_cpu_fraction` fails because `multiprocessing.Pool` receives `processes=0`, raising `ValueError("Number of processes must be at least 1")`.

**Evidence:**
- Stack trace shows: `Run()` → `linter.check()` → `check_parallel()` → `multiprocessing.Pool(processes=0)`
- Error: `ValueError: Number of processes must be at least 1` at `multiprocessing/pool.py:205`

## H₁ (deduction): Root cause traced
**Status:** CONFIRMED
**Mode:** Deduction (code analysis)
**Confidence:** 99%

When running with `--jobs=0` in a Kubernetes container with fractional CPU allocation (cpu.shares=2), the call chain produces a 0 value that crashes multiprocessing:

1. `run.py:185`: When `linter.config.jobs == 0`, calls `_cpu_count()`
2. `run.py:68`: `_cpu_count()` calls `_query_cpu()`
3. `run.py:60`: `_query_cpu()` reads `/sys/fs/cgroup/cpu/cpu.shares` (value: 2)
4. `run.py:60`: Calculates `avail_cpu = int(cpu_shares / 1024) = int(2/1024) = 0`
5. `run.py:61`: Returns 0
6. `run.py:77-78`: `cpu_share = 0`, returns `min(0, cpu_count) = 0`
7. `run.py:185`: `linter.config.jobs = 0`
8. `parallel.py:140`: Creates `multiprocessing.Pool(0)` → ValueError

**Supporting evidence:**
- `pylint/lint/run.py:60` — `avail_cpu = int(cpu_shares / 1024)`
- `pylint/lint/run.py:77-78` — `if cpu_share is not None: return min(cpu_share, cpu_count)`
- Test mocks cpu.shares to 2, triggering the fractional CPU case

## H₂ (deduction): Fix location
**Status:** PROPOSED
**Mode:** Deduction
**Confidence:** 95%

The fix should be in `_cpu_count()` at line 77-78, not in `_query_cpu()`, because:
- `_query_cpu()` is designed to detect the actual container CPU limit (even if fractional)
- `_cpu_count()` is the function that provides a usable CPU count for job parallelism
- The constraint "at least 1 CPU" is a multiprocessing requirement, not a container detection concern

**Edit site:**
`pylint/lint/run.py:77-78` — Change `return min(cpu_share, cpu_count)` to `return max(1, min(cpu_share, cpu_count))`

This ensures the returned value is always >= 1, satisfying `multiprocessing.Pool`'s requirements.


## Gate Loop: Iteration 1

**Drafted fix:** Added `max(1, ...)` clamps to both return paths in `_cpu_count()` to ensure the function always returns at least 1 process.

**codex review:** Confirmed the fix addresses the crash path. Suggested clamping both returns (cpu_share path and fallback path) to enforce the invariant that `_cpu_count()` never returns < 1.

**Diff applied:**
```diff
--- a/pylint/lint/run.py
+++ b/pylint/lint/run.py
@@ -75,9 +75,9 @@ def _cpu_count() -> int:
     else:
         cpu_count = 1
     if cpu_share is not None:
-        return min(cpu_share, cpu_count)
-    return cpu_count
+        return max(1, min(cpu_share, cpu_count))
+    return max(1, cpu_count)
```

**Gate result:** ✅ **PASS** — All 9 tests passed, including `test_pylint_run_jobs_equal_zero_dont_crash_with_cpu_fraction`

**Trajectory:** Convergent-resolved (fix addresses root cause directly, no iterations needed)

---

# Audit: pylint-dev__pylint-6903

## FAIL_TO_PASS
- `tests/test_pylint_runners.py::test_pylint_run_jobs_equal_zero_dont_crash_with_cpu_fraction`: **PASS** ✓

## PASS_TO_PASS regressions
**None** — all 8 PASS_TO_PASS tests passed:
- `test_runner[run_epylint]`: PASS
- `test_runner[run_pylint]`: PASS
- `test_runner[run_pyreverse]`: PASS
- `test_runner[run_symilar]`: PASS
- `test_runner_with_arguments[run_epylint]`: PASS
- `test_runner_with_arguments[run_pylint]`: PASS
- `test_runner_with_arguments[run_pyreverse]`: PASS
- `test_runner_with_arguments[run_symilar]`: PASS

## Pre-existing failures (not counted, confirmed against base capture)
**None** — the only failure in the base capture was the FAIL_TO_PASS test itself.

## Result
The patch successfully fixes the root cause:
- Added `max(1, ...)` clamps to both return paths in `_cpu_count()` (lines 78, 79)
- Ensures the function always returns at least 1, satisfying `multiprocessing.Pool()`'s requirement
- No regressions introduced
- All 9 tests pass
