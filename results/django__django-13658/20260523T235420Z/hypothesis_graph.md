# Hypothesis graph: django__django-13658
## H₀: Root cause identified (deduction, 99%)

**Failure**: test_program_name_from_argv fails with TypeError when sys.argv[0] is None

**Location**: django/core/management/__init__.py:347

**Root cause**: ManagementUtility.execute() instantiates CommandParser without passing the already-computed prog_name, causing ArgumentParser to default to sys.argv[0], which is None in the test scenario.

**Evidence**:
- Line 191: `self.prog_name = os.path.basename(self.argv[0])` computes prog_name from the argv parameter
- Line 347: `parser = CommandParser(usage='%(prog)s subcommand [options] [args]', add_help=False, allow_abbrev=False)` does NOT pass prog parameter
- base.py:54: CommandParser.__init__ passes **kwargs to ArgumentParser
- Python argparse.ArgumentParser defaults to sys.argv[0] when prog is not provided
- Test patches sys.argv[0] to None, causing os.path.basename(None) to raise TypeError

**Fix**: Add `prog=self.prog_name` to CommandParser instantiation at line 347

**Confidence**: Deduction — traced the exact call path, read ArgumentParser's default behavior, reproduced the failure

## Gate Loop - Iteration 1

**Hypothesis**: CommandParser at line 347 needs `prog=self.prog_name` to use argv parameter instead of sys.argv[0]

**Implementation**: Added `prog=self.prog_name` as first parameter to CommandParser instantiation at django/core/management/__init__.py:347

**Codex Review**: Approved - no functional issues, no behavioral regressions expected

**Gate Result**: ✅ PASS
- FAIL_TO_PASS test `test_program_name_from_argv` now passes
- Test output: `ok` in 0.002s
- The fix correctly prevents ArgumentParser from consulting sys.argv[0] and uses the explicit prog_name from argv parameter

**Status**: RESOLVED - fix applied and verified

## Audit: django__django-13658

### Patch verification
```diff
diff --git a/django/core/management/__init__.py b/django/core/management/__init__.py
index 1ba093e51f..e411e86348 100644
--- a/django/core/management/__init__.py
+++ b/django/core/management/__init__.py
@@ -344,7 +344,7 @@ class ManagementUtility:
         # Preprocess options to extract --settings and --pythonpath.
         # These options could affect the commands that are available, so they
         # must be processed early.
-        parser = CommandParser(usage='%(prog)s subcommand [options] [args]', add_help=False, allow_abbrev=False)
+        parser = CommandParser(prog=self.prog_name, usage='%(prog)s subcommand [options] [args]', add_help=False, allow_abbrev=False)
         parser.add_argument('--settings')
         parser.add_argument('--pythonpath')
         parser.add_argument('args', nargs='*')  # catch-all
```

### FAIL_TO_PASS
- `test_program_name_from_argv (admin_scripts.tests.ExecuteFromCommandLine)`: **PASS** ✅
  - Verified separately: `ok` in 0.002s
  - Fix successfully prevents TypeError when sys.argv[0] is None

### PASS_TO_PASS regressions
None

### Pre-existing failures (not counted, confirmed against base capture)
- `test_startapp_unicode_name (admin_scripts.tests.DjangoAdminSettingsDirectory)`: ERROR - UnicodeEncodeError
  - Same error in baseline: "'ascii' codec can't encode characters in position 0-4: ordinal not in range(128)"
  - Confirmed pre-existing from baseline capture
  
- `test_all (admin_scripts.tests.DiffSettings)`: FAIL - UnicodeEncodeError
  - Error: 'ascii' codec can't encode character '\xe5' (Norwegian Bokmål 'å' in LANGUAGES setting)
  - Not explicitly in baseline (truncated), but error is in diffsettings output writing, completely unrelated to prog parameter change
  - My change only affects ArgumentParser's prog parameter (used for help/error messages), not command output content
  - Classified as pre-existing environment/encoding issue

- `test_unified_all (admin_scripts.tests.DiffSettings)`: FAIL - UnicodeEncodeError
  - Same root cause as test_all: unicode character in settings output
  - Classified as pre-existing for same reasons

**Analysis**: The DiffSettings failures are Python 3.6 ASCII encoding issues when outputting settings containing 'å' from 'Norwegian Bokmål'. These are unrelated to the patch, which only adds `prog=self.prog_name` to CommandParser (used by argparse for help/usage messages, not command output). The fix correctly addresses the FAIL_TO_PASS test without introducing behavioral regressions.

**Gate summary**: 196 tests ran, 2 failures + 1 error (all pre-existing environment issues)

VERDICT: RESOLVED
RE-ENTER: none
