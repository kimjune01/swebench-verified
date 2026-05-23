# Hypothesis graph: pytest-dev__pytest-7982

## Hypothesis H₀: Initial diagnosis (abduction)

**Node**: H₀
**Type**: abduction
**Status**: active
**Confidence**: 95% (deduction)

### Observation
Test `test_collect_symlink_dir` fails with:
```
AssertionError: assert {'passed': 1} != {'passed': 2}
```

Expected 2 tests to pass (one from `dir/test_it.py` and one from `symlink_dir/test_it.py`), but only 1 test was collected from `dir/test_it.py`. The symlinked directory `symlink_dir` was not followed during collection.

### Root Cause
In `src/_pytest/pathlib.py:561`, the `visit()` function checks directories with:
```python
if entry.is_dir(follow_symlinks=False) and recurse(entry):
```

The `follow_symlinks=False` parameter prevents symlinks to directories from being recognized as directories. When `follow_symlinks=False`, a symlink to a directory returns `False` from `is_dir()`, so the directory is never recursed into.

This was introduced in commit `3633b691d` (part of merge commit `b473e515bc57ff1133fe650f1e7e6d7e22e5d841` mentioned in the issue) when migrating from `py.path.local` to `os.scandir`. The old code using `entry.check(dir=1)` followed symlinks by default.

### Supporting Evidence
- `src/_pytest/pathlib.py:561`: `if entry.is_dir(follow_symlinks=False) and recurse(entry):`
- `os.DirEntry.is_dir()` default is `follow_symlinks=True`
- Git history shows this parameter was added in commit `3633b691d`
- Other tests like `test_collect_sub_with_symlinks` pass because they test symlinked files, not symlinked directories
- Symlinked files work because the `is_file()` check doesn't have `follow_symlinks=False`

### Edit Sites
1. `src/_pytest/pathlib.py` line 561: Change `entry.is_dir(follow_symlinks=False)` to `entry.is_dir()` (or explicitly `entry.is_dir(follow_symlinks=True)`)


## Craft iteration 1

**Action**: Applied minimal fix - removed `follow_symlinks=False` parameter from `entry.is_dir()` at line 561 of `src/_pytest/pathlib.py`.

**Codex review**: Raised valid concerns about symlink cycles and infinite recursion. Suggested need for cycle detection and additional tests. However, craft directive is minimal fix - let gate arbitrate.

**Gate result**: ✅ GREEN
- FAIL_TO_PASS test `testing/test_collection.py::test_collect_symlink_dir` now PASSES
- All 79 tests in test_collection.py pass (1 xfailed as expected)
- No regressions in existing symlink tests:
  - test_collect_symlink_file_arg
  - test_collect_symlink_out_of_tree
  - test_collect_sub_with_symlinks[True/False]

**Resolution**: Fix complete. The working tree contains the minimal change that makes FAIL_TO_PASS pass without breaking existing tests.

## Audit: pytest-dev__pytest-7982

### Phase 1: Patch verification
```
src/_pytest/pathlib.py | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```
Patch is live in the tree.

### Phase 2: Gate execution
Ran full gate - 79 passed, 1 xfailed (expected) in testing/test_collection.py

### Phase 3: Classification

#### FAIL_TO_PASS
- `testing/test_collection.py::test_collect_symlink_dir` → **PASSED** ✓

#### PASS_TO_PASS regressions
**None** - all 79 tests in test_collection.py pass, including all specified PASS_TO_PASS tests.

#### Pre-existing failures (not counted, confirmed against base capture)
- `tests/test_foo.py::test_check` - ModuleNotFoundError (present in base capture, not in FAIL_TO_PASS or PASS_TO_PASS lists)

### Phase 4: Verdict
All FAIL_TO_PASS tests now pass. Zero PASS_TO_PASS regressions. The minimal fix (removing `follow_symlinks=False` from `entry.is_dir()` call) successfully resolves the symlink directory collection issue without introducing any regressions.

VERDICT: RESOLVED
RE-ENTER: none
