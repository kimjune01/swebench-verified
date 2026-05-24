# Hypothesis graph: django__django-11749

## H₀: Initial diagnosis - call_command doesn't handle required mutually exclusive groups

**Mode**: Abduction (pattern recognition from code reading)
**Confidence**: 95% (deduction from traced code path)

### Observation
The test `test_mutually_exclusive_group_required_options` fails when calling:
```python
management.call_command('mutually_exclusive_required', foo_id=1, stdout=out)
```

Error: `django.core.management.base.CommandError: Error: one of the arguments --foo-id --foo-name is required`

The command defines a required mutually exclusive group:
```python
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('--foo-id', type=int, nargs='?', default=None)
group.add_argument('--foo-name', type=str, nargs='?', default=None)
```

### Root cause
In `django/core/management/__init__.py`, the `call_command` function (lines 135-138) only passes arguments to `parse_args` if the individual action is marked as `required`:

```python
parse_args += [
    '{}={}'.format(min(opt.option_strings), arg_options[opt.dest])
    for opt in parser_actions if opt.required and opt.dest in options
]
```

However, in argparse, when arguments belong to a required mutually exclusive group:
- The **group** has `required=True`
- The **individual arguments** have `required=False`

Therefore, when `foo_id=1` is passed via kwargs:
1. It's not in `parse_args` because the action has `required=False`
2. The parser's `parse_args()` is called without seeing `foo_id`
3. The parser still sees an unsatisfied required mutually exclusive group
4. The parser raises an error

### Supporting evidence
- `django/core/management/__init__.py:135-138` - only checks `opt.required`
- Verified via Python: `group._group_actions[0].required == False` even when `group.required == True`
- Parser structure: `parser._mutually_exclusive_groups` contains groups with `group.required` and `group._group_actions`

### Edit sites
**Primary edit**: `django/core/management/__init__.py` lines 132-138

Need to add logic after collecting regular required arguments to also handle required mutually exclusive groups:

1. Create a helper function (similar to `get_actions`) to yield all mutually exclusive groups from parser and subparsers
2. For each group where `group.required == True`:
   - Check if any of `group._group_actions` has `action.dest` in `options`
   - If yes, add that option to `parse_args` using the same format as line 136

This should go between line 138 and line 139 (after building parse_args for regular required args, before calling parse_args).

### Test coverage
The failing test already validates the fix:
- Passing `foo_id=1` should work (first assertion)
- Passing `foo_name='foo'` should work (second assertion)  
- Passing neither should raise error (third assertion)


## Craft: Gate Loop

### Iteration 1: Initial Fix

**Drafted fix:**
Added `get_mutually_exclusive_groups()` helper to recursively collect groups from parser and subparsers, then iterate over required groups to add their actions to `parse_args` when present in `arg_options`.

**Codex feedback (pre-gate):**
- Handle action types correctly (store_true/false/const use just `--flag`, others use `--flag=value`)
- Don't break early - add all matching options so argparse can detect conflicts
- Track added dests to avoid duplicating aliases

**Applied fix:**
```python
def get_mutually_exclusive_groups(parser):
    for group in parser._mutually_exclusive_groups:
        yield group
    for opt in parser._actions:
        if isinstance(opt, _SubParsersAction):
            for sub_opt in opt.choices.values():
                yield from get_mutually_exclusive_groups(sub_opt)

added_from_groups = set()
for group in get_mutually_exclusive_groups(parser):
    if group.required:
        for opt in group._group_actions:
            if opt.dest in arg_options and opt.dest not in added_from_groups and opt.option_strings:
                opt_string = min(opt.option_strings)
                if opt.nargs == 0:
                    parse_args.append(opt_string)
                else:
                    parse_args.append('{}={}'.format(opt_string, arg_options[opt.dest]))
                added_from_groups.add(opt.dest)
```

**Gate result:** ✅ PASS — all 35 tests pass including `test_mutually_exclusive_group_required_options`

**Trajectory:** Convergent (success) — first iteration resolved the issue.

---

# Audit: django__django-11749

## FAIL_TO_PASS
- test_mutually_exclusive_group_required_options (user_commands.tests.CommandTests): PASS ✓

## PASS_TO_PASS regressions
none

## Pre-existing (not counted, confirmed against base capture)
none

## Summary
The patch successfully resolves the issue. The `call_command()` function now properly handles mutually exclusive required groups by:
1. Recursively collecting mutually exclusive groups from parsers and subparsers
2. Adding options from required mutually exclusive groups to parse_args
3. Tracking which dests have been added to avoid duplicates

All 35 tests pass, including the target FAIL_TO_PASS test that was ERROR on base.

VERDICT: RESOLVED
RE-ENTER: none
