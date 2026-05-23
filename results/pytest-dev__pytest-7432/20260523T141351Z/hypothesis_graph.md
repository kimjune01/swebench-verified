# Hypothesis graph: pytest-dev__pytest-7432

## H₀: Initial observation (abduction)

The test `test_xfail_run_with_skip_mark[test_input1-expected1]` fails because when `--runxfail` is used with `@pytest.mark.skip`, the skip location is reported as `src/_pytest/skipping.py:239` instead of `test_sample.py:2`.

**Evidence:**
- Test expects: `SKIPPED [1] test_sample.py:2: unconditional skip`
- Actual output: `SKIPPED [1] ../../../../testbed/src/_pytest/skipping.py:239: unconditional skip`

## H₁: Root cause (deduction, 98%)

The bug is in `src/_pytest/skipping.py` in the `pytest_runtest_makereport` hook function (lines 261-303).

The function has an if/elif chain:
1. Line 266-272: Handle unittest unexpected success
2. Line 272-273: `elif item.config.option.runxfail: pass` - skip xfail processing when --runxfail is set
3. Line 274-277: Handle xfail.Exception
4. Line 278-293: Handle xfailed items
5. Line 295-303: Fix skip location for `@pytest.mark.skip` and `@pytest.mark.skipif`

**The bug:** Branch #2 (`elif item.config.option.runxfail: pass`) blocks execution of branch #5 (the skip location fix).

**Why this is wrong:**
- The `--runxfail` option should only affect xfail test behavior (branches #3 and #4)
- It should NOT affect skip mark behavior (branch #5)
- Skip location fixing is independent of xfail processing

**Call flow when `@pytest.mark.skip` is used:**
1. `pytest_runtest_setup` (line 234-239): sets `skipped_by_mark_key = True`, calls `skip(skipped.reason)` at line 239
2. The `skip()` call raises a Skip exception from line 239 in skipping.py
3. `pytest_runtest_makereport` (line 261+): should fix the location to point to the test definition
   - Without `--runxfail`: reaches branch #5, fixes location ✓
   - With `--runxfail`: hits branch #2, returns early, never fixes location ✗

**Supporting evidence:**
- `src/_pytest/skipping.py:239` = `skip(skipped.reason)` - where Skip exception is raised internally
- `src/_pytest/skipping.py:295-303` = skip location fix that replaces internal location with test location
- `src/_pytest/skipping.py:272-273` = `elif runxfail: pass` that blocks the location fix

**Confidence:** 98% (deduction) - traced the exact code path, identified the blocking conditional


## craft: gate iteration 1

**Action:** Changed line 294 from `elif (` to `if (` to make skip location fix independent of the `--runxfail` branch.

**codex pre-gate review:** Raised concern that converting `elif` to `if` might over-apply location rewrite to imperative `pytest.skip()` or `pytest.xfail()` calls. However, `skipped_by_mark_key` guard should prevent this.

**Gate result:** GREEN - all 79 tests passed, including FAIL_TO_PASS test `testing/test_skipping.py::TestXFail::test_xfail_run_with_skip_mark[test_input1-expected1]`.

**Resolution:** The fix is correct. The `skipped_by_mark_key` condition properly guards against rewriting locations for non-decorator skips. The `--runxfail` option no longer blocks the skip location fix for `@pytest.mark.skip`.

## audit: pytest-dev__pytest-7432

### Patch verification
- Patch is live: 1 file changed (src/_pytest/skipping.py), changed `elif` to `if` on line 294
- Change: Made skip location fix independent of `--runxfail` branch

### FAIL_TO_PASS results
- `testing/test_skipping.py::TestXFail::test_xfail_run_with_skip_mark[test_input1-expected1]`: **PASSED** ✓

### PASS_TO_PASS regressions
None. All 79 tests passed.

### Pre-existing failures (not counted)
None observed in gate output.

### Gate summary
- Total: 79 passed in 1.56s
- FAIL_TO_PASS: 1/1 passing
- PASS_TO_PASS regressions: 0
- Pre-existing failures: 0

### Verdict justification
All FAIL_TO_PASS tests pass, zero PASS_TO_PASS regressions → fix is complete and correct.

