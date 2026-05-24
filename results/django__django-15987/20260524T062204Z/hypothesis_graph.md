# Hypothesis graph: django__django-15987

## H₀ (abduction)
The tests fail because the duplicate fixture directory detection in `loaddata.py` compares a string path (`app_dir`) against entries in `fixture_dirs` that may be `pathlib.Path` objects, and the `in` operator returns `False` when comparing strings to Path objects even if they represent the same filesystem path.

**Evidence:**
- Test `test_fixture_dirs_with_default_fixture_path_as_pathlib` sets `FIXTURE_DIRS=[Path(_cur_dir) / "fixtures"]` (a Path object)
- Test expects `ImproperlyConfigured` exception but it's not raised
- Similar test `test_fixture_dirs_with_default_fixture_path` with string path `os.path.join(_cur_dir, "fixtures")` passes correctly

## H₁ (deduction - 95% confidence)
**Root cause:** The `fixture_dirs` cached property in `django/core/management/commands/loaddata.py` fails to normalize `pathlib.Path` objects to strings before performing duplicate detection and default directory validation. This causes the `in` operator comparison to fail when comparing string paths against Path objects, even when they represent identical filesystem locations.

**Code path:**
1. `loaddata.py:364` - `fixture_dirs = settings.FIXTURE_DIRS` retrieves the raw configuration which may contain `pathlib.Path` instances
2. `loaddata.py:365` - Duplicate check `len(fixture_dirs) != len(set(fixture_dirs))` would fail to detect string/Path duplicates
3. `loaddata.py:369` - `app_dir = os.path.join(app_config.path, "fixtures")` creates a string path
4. `loaddata.py:370` - `if app_dir in fixture_dirs:` returns False when `fixture_dirs` contains Path objects (string != Path)
5. `loaddata.py:383` - `return [os.path.realpath(d) for d in dirs]` normalizes all paths, but AFTER the validation checks

**Supporting evidence:**
- `loaddata.py:369-370` - app_dir is always a string, but fixture_dirs may contain Path objects
- `loaddata.py:383` - The final return correctly normalizes all paths with os.path.realpath, showing the intended canonical form
- Python behavior: `"/tmp/fixtures" in [Path("/tmp/fixtures")]` returns `False`
- Python behavior: `len(["/tmp/fixtures", Path("/tmp/fixtures")]) != len(set(["/tmp/fixtures", Path("/tmp/fixtures")]))` is False (doesn't detect duplicate)

**What must change:**
Normalize `fixture_dirs` paths to canonical string form immediately after retrieval from settings, before any validation checks. Also normalize `app_dir` to ensure consistent comparison.

## craft gate-loop

### Iteration 1: Initial fix applied

**Changes**:
- Line 365: Added `fixture_dirs = [os.path.realpath(d) for d in fixture_dirs]` to normalize Path objects to canonical string paths before validation
- Line 371: Changed `if app_dir in fixture_dirs:` to `if os.path.realpath(app_dir) in fixture_dirs:` for consistent comparison

**codex review**: Approved cleaner approach that preserves error message format while fixing comparison. Keeps `app_dir` as-is for the error message but normalizes both sides for comparison.

**Gate result**: ✅ PASS
- All 58 tests passed
- `test_fixture_dirs_with_default_fixture_path_as_pathlib` now correctly raises `ImproperlyConfigured` when FIXTURE_DIRS contains a Path object pointing to a default fixture directory

**Resolution**: The fix correctly handles pathlib.Path objects in settings.FIXTURE_DIRS by normalizing all paths to canonical string form before validation checks (duplicate detection and default directory check), while preserving the original path format in error messages.

---

# Audit: django__django-15987

## Patch verification
Patch is live in working tree:
```
django/core/management/commands/loaddata.py | 3 ++-
1 file changed, 2 insertions(+), 1 deletion(-)
```

Changes:
- Line 365: Normalize `fixture_dirs` with `os.path.realpath()` before validation
- Line 371: Normalize `app_dir` with `os.path.realpath()` for consistent comparison

## FAIL_TO_PASS
- `test_fixture_dirs_with_default_fixture_path`: **PASS** ✓
- `test_fixture_dirs_with_default_fixture_path_as_pathlib`: **PASS** ✓

## PASS_TO_PASS regressions
**None** — all 58 tests passed (1 skipped for database feature support, expected).

All PASS_TO_PASS tests verified:
- `test_fixtures_loaded (fixtures_regress.tests.TestLoadFixtureFromOtherAppDirectory)`: ok
- Natural key and M2M dependency tests: all ok
- All other fixture regression tests: ok

## Pre-existing failures (confirmed against base capture)
**None** — the baseline capture showed all tests passing except the FAIL_TO_PASS tests.

## Kill report
Not applicable — patch is RESOLVED.

The fix correctly normalizes both `fixture_dirs` (which may contain `pathlib.Path` objects from settings) and `app_dir` (string from `os.path.join`) to canonical string paths using `os.path.realpath()` before comparison. This ensures the duplicate detection and default directory validation work correctly regardless of whether paths are specified as strings or Path objects, and handles symbolic links and relative paths.

