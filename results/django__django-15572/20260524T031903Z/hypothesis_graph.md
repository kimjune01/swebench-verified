# Hypothesis graph: django__django-15572

## H0: Empty string in DIRS converts to project root (ACTIVE)

**Type:** Abduction  
**Confidence:** 95% (deduction from code trace)

**Evidence:**
- Test failure: `test_template_dirs_ignore_empty_path` expects `set()` but gets `{PosixPath('/testbed')}`
- `django/template/autoreload.py:20` processes `backend.engine.dirs` with: `cwd / to_path(dir) for dir in backend.engine.dirs`
- When `dir=""`: `Path("")` becomes `Path('.')`, and `cwd / Path('.')` resolves to `cwd` itself
- Verified: `Path.cwd() / Path("") == Path.cwd()` → `/testbed`

**Root cause:**
Line 20 in `django/template/autoreload.py` does not filter empty strings before Path normalization. The regression was introduced in commit 68357b2ca9 which changed from `items.update(backend.engine.dirs)` to `items.update(cwd / to_path(dir) for dir in backend.engine.dirs)`.

**Impact:**
When empty string is in template dirs, the project root gets added to watched directories, causing `template_changed()` to always return True for any file, breaking autoreload for code changes.

**Edit sites:**
1. `django/template/autoreload.py:20` - Filter empty/falsy dirs before Path normalization
2. `django/template/autoreload.py:26-29` - Same filter needed for loader.get_dirs() (defensive, less common issue)

**Fix approach:**
Add `if dir` filter in the generator expression on line 20, and `if directory` filter on line 27.

## Gate Loop - Iteration 1

**Hypothesis tested:** Empty string in `backend.engine.dirs` converts to project root via Path normalization

**Edit applied:**
- `django/template/autoreload.py:20` - Added filter `if dir != ""` to exclude empty strings from `backend.engine.dirs`
- `django/template/autoreload.py:27` - Added filter `if directory != ""` to exclude empty strings from `loader.get_dirs()`

**codex pre-gate review:** Patch is basically correct, recommended using explicit `!= ""` instead of truthy checks for clarity. No breakage expected.

**Gate result:** ✅ PASS (11/11 tests)
- `test_template_dirs_ignore_empty_path` ✅ PASS
- All other autoreload tests ✅ PASS

**Trajectory:** Convergent success - first iteration resolved the issue

**Resolution:** The recon diagnosis was correct. Filtering empty strings before Path normalization prevents the project root from being added to template directories.

---

# Audit: django__django-15572

## FAIL_TO_PASS
- test_template_dirs_ignore_empty_path: **PASS** ✅

## PASS_TO_PASS regressions
None — all 10 PASS_TO_PASS tests remain passing.

## Pre-existing (not counted, confirmed against base capture)
None.

## Verdict Summary
The patch successfully resolves the issue:
- The single FAIL_TO_PASS test now passes
- Zero regressions introduced
- All 11 tests in the suite pass

The fix correctly filters empty strings before Path normalization in both `backend.engine.dirs` processing (line 20) and `loader.get_dirs()` processing (line 27), preventing the project root from being incorrectly added to template directories.
