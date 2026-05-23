# Hypothesis graph: django__django-11292

## H₀ (abduction, initial): Missing --skip-checks command-line argument

The test `test_skip_checks` fails because the `--skip-checks` option is not defined in the argument parser.

**Evidence:**
- Error message: `manage.py set_option: error: unrecognized arguments: --skip-checks`
- `django/core/management/base.py:226` defines `base_stealth_options = ('skip_checks', 'stderr', 'stdout')` - options that can be passed programmatically but not from command line
- `django/core/management/base.py:360` uses the option: `if self.requires_system_checks and not options.get('skip_checks'):`
- `django/core/management/base.py:249-290` defines `create_parser` method which adds command-line arguments, but `--skip-checks` is not added

**Root cause (deduction, 95%):**
The `--skip-checks` argument is not added to the argument parser in the `create_parser` method of `BaseCommand`. The option exists as a "stealth option" for programmatic use but is not exposed on the command line.

**Edit sites:**
1. `django/core/management/base.py:97-99` - Add `'--skip-checks'` to the `show_last` set
2. `django/core/management/base.py:281-282` - Add `parser.add_argument('--skip-checks', action='store_true', help='Skip system checks.')` after the `--traceback` argument
3. `django/core/management/base.py:226` - Remove `'skip_checks'` from `base_stealth_options` tuple (change to `base_stealth_options = ('stderr', 'stdout')`)


## Craft Phase

### Gate iteration 1

**Changes applied:**
1. Added `'--skip-checks'` to `show_last` set (line 98) for help text ordering
2. Removed `'skip_checks'` from `base_stealth_options` tuple (line 226) since now parser-defined
3. Added `parser.add_argument('--skip-checks', action='store_true', help='Skip system checks.')` after `--traceback` (line 281)

**codex pre-gate review:** Structurally sound. Parser addition makes CLI surface available; execute() already honors the option. Backward-compatible with programmatic call_command(skip_checks=True).

**Gate result:** ✅ PASS - All 32 tests pass including `test_skip_checks` (FAIL_TO_PASS) and `test_call_command_no_checks` (backward compatibility verified).

**Trajectory:** Convergent success - first attempt resolved the issue.

---

# Audit: django__django-11292

## FAIL_TO_PASS
- test_skip_checks (user_commands.tests.CommandRunTests): **PASS** ✓

## PASS_TO_PASS regressions
None

## Pre-existing (not counted, confirmed against base capture)
None

## Summary
The patch successfully resolves the issue. The `--skip-checks` option is now properly registered in the argument parser by:
1. Adding it to the `show_last` set in DjangoHelpFormatter
2. Removing it from `base_stealth_options` (making it visible)
3. Explicitly adding `parser.add_argument('--skip-checks', ...)` in `create_parser()`

All 32 tests pass with no regressions.

VERDICT: RESOLVED
RE-ENTER: none
