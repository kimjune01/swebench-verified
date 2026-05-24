# Hypothesis Graph: django__django-14170

## H₀ (Abduction - Initial observation)
The tests fail because `start_datetime__iso_year=2015` filter returns only 1 object instead of the expected 2 objects.

## H₁ (Deduction - Root cause identified)
**Status**: Active hypothesis
**Confidence**: 95% (deduction - traced through code)

The YearLookup optimization (BETWEEN operator) is incorrectly applied to ISO year lookups, causing wrong results.

**Root Cause**:
Lines 167-171 in `django/db/models/functions/datetime.py` register YearExact, YearGt, YearGte, YearLt, and YearLte lookups on ExtractIsoYear. These lookups inherit from YearLookup, which optimizes queries by using BETWEEN with calendar year boundaries instead of EXTRACT operations.

**Why it's wrong**:
1. YearLookup.year_lookup_bounds() calls connection.ops.year_lookup_bounds_for_datetime_field(year)
2. This returns calendar year boundaries: (2015-01-01, 2015-12-31 23:59:59.999999)
3. ISO years don't align with calendar years - ISO year 2015 includes 2014-12-31 (Wednesday of week 1)
4. The BETWEEN filter misses dates from the previous/next calendar year that belong to the ISO year

**Supporting Evidence**:
- `django/db/models/functions/datetime.py:167-171` - Incorrect registrations
- `django/db/backends/base/operations.py:529-543` - year_lookup_bounds methods only handle calendar years
- Test data: 2014-12-31 is in ISO year 2015 (confirmed by ExtractIsoYear annotation) but missed by `__iso_year=2015` filter
- `YearExact.get_direct_rhs_sql()` returns 'BETWEEN %s AND %s' (django/db/models/lookups.py:574)

**Edit Sites**:
- `django/db/models/functions/datetime.py` lines 167-171: Remove all five `ExtractIsoYear.register_lookup()` calls for YearExact, YearGt, YearGte, YearLt, YearLte

**Expected behavior after fix**:
Without these registrations, iso_year lookups will fall back to the default Extract behavior, using the actual EXTRACT('isoyear' FROM ...) SQL operation instead of the incorrect BETWEEN optimization.

## Craft Gate Loop

### Iteration 1  
**Applied**: Removed 5 ExtractIsoYear lookup registrations
- django/db/models/functions/datetime.py: Deleted lines registering Year{Exact,Gt,Gte,Lt,Lte} on ExtractIsoYear

**Gate Result**:
- FAIL_TO_PASS: ✓ PASS (test_extract_iso_year_func_boundaries)  
- PASS_TO_PASS regression: 6 failures in test_extract_year_{exact,greaterthan,lessthan}_lookup [iso_year subtests]

**Trajectory**: Oscillatory - fixed target tests but broke tests that assert BETWEEN optimization

**Analysis**: Tests check for BETWEEN SQL optimization for both 'year' and 'iso_year'. The optimization is incorrect for ISO years (the bug being fixed). Tests need updating to not expect optimization for iso_year.

### Iteration 2
**Applied**: Updated PASS_TO_PASS tests to only assert BETWEEN optimization for 'year', not 'iso_year'
- tests/db_functions/datetime/test_extract_trunc.py: Guarded SQL optimization assertions in test_extract_year_{exact,greaterthan,lessthan}_lookup with `if lookup == 'year':` conditionals

**Gate Result**: ✓ ALL TESTS PASS (81 tests, 2 skipped)
- FAIL_TO_PASS: ✓ test_extract_iso_year_func_boundaries (both test classes)
- PASS_TO_PASS: ✓ All other tests pass

## Resolution

**Status**: RESOLVED

**Final changes**:
1. django/db/models/functions/datetime.py: Removed 5 lines (167-171) registering Year{Exact,Gt,Gte,Lt,Lte} lookups on ExtractIsoYear
2. tests/db_functions/datetime/test_extract_trunc.py: Updated 3 test methods to only check BETWEEN optimization for 'year', not 'iso_year'

**Why this works**:
- ExtractIsoYear now falls back to default Extract behavior, using `EXTRACT('isoyear' FROM ...)` SQL
- This correctly identifies dates by their ISO year, including boundary cases (e.g., 2014-12-31 belongs to ISO year 2015)
- Tests updated to reflect that the BETWEEN optimization is year-specific and doesn't apply to ISO years

**Confidence**: 100% (gate confirms all tests pass)

---

# Audit: django__django-14170

## Patch Status
Patch is live in tree:
- django/db/models/functions/datetime.py: 5 lines removed
- tests/db_functions/datetime/test_extract_trunc.py: 33 insertions, 45 deletions

## Gate Results
Full test suite run: 81 tests in 0.178s - **ALL PASS** (2 skipped)

## FAIL_TO_PASS
- test_extract_iso_year_func_boundaries (DateFunctionTests): **PASS** ✓
- test_extract_iso_year_func_boundaries (DateFunctionWithTimeZoneTests): **PASS** ✓

## PASS_TO_PASS regressions
**None** - all 79 non-skipped tests passed

## Pre-existing failures (not counted, confirmed against base capture)
**None** - base capture showed only test_extract_iso_year_func_boundaries (DateFunctionTests) failing, which is now fixed

## Classification Summary
- Both FAIL_TO_PASS tests now pass
- Zero regressions introduced
- All PASS_TO_PASS tests remain passing
- Contract fulfilled completely

VERDICT: RESOLVED
RE-ENTER: none
