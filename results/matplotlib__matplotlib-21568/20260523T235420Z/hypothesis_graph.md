# Hypothesis graph: matplotlib__matplotlib-21568

## H₀: Initial observation (abduction)
The tests fail because colons in datetime format strings are not being escaped in TeX math mode. The test expectations show that colons should be escaped as `{:}` (e.g., `$\mathdefault{04{:}00}$`) but the actual output has unescaped colons (e.g., `$\mathdefault{04:00}$`).

**Confidence**: 95% (deduction from test failure diff)
**Evidence**:
- Test failure shows: Expected `'$\\mathdefault{00{:}00}$'` but got `'$\\mathdefault{00:00}$'`
- Affects 4 test cases: hours and minutes formatting in both AutoDateFormatter and ConciseDateFormatter

## H₁: Root cause (deduction)
The `_wrap_in_tex()` function in `lib/matplotlib/dates.py` (lines 594-601) escapes dashes as `{-}` to prevent them from being treated as binary operators in TeX math mode, but does not escape colons. In TeX math mode, colons should also be escaped as `{:}` to ensure proper spacing, similar to how dashes are handled.

**Confidence**: 99% (deduction - traced through code and git history)
**Evidence**:
- `lib/matplotlib/dates.py:599` only escapes dashes: `.replace('-', '{-}')`
- Both AutoDateFormatter and ConciseDateFormatter use `_wrap_in_tex()` when `usetex=True`
- Git history shows commit 5a8fc07d5d simplified `_wrap_in_tex` but didn't escape colons
- Test patch 43ce4b7cb6 added expectations for escaped colons to fix spacing issues in TeX mode

## H₂: Edit specification
Add colon escaping to `_wrap_in_tex()` function, immediately after dash escaping.

**File**: `lib/matplotlib/dates.py`
**Line**: 599
**Change**: After the line that replaces dashes, add colon replacement: `.replace(':', '{:}')`

The change should be chained with the dash replacement to maintain consistency.

## Gate Loop - Iteration 1

**Trajectory**: Divergent (progress)

**Changes made**:
1. `lib/matplotlib/dates.py:598-599` - Updated `_wrap_in_tex()`:
   - Changed comment to "Braces prevent TeX math mode from adding operator spacing."
   - Added `.replace(':', '{:}')` to escape colons like dashes

**Gate result**: Syntax error - invalid escape sequence in line 599

**Issue**: String concatenation error - had `+'}'$` instead of `+'}$'`

---

## Gate Loop - Iteration 2

**Trajectory**: Convergent (different issue)

**Changes made**:
- Fixed syntax error in line 599 - corrected string to end with `+'}$'`

**Gate result**: 2 of 4 FAIL_TO_PASS tests still failing
- PASSED: test_concise_formatter_usetex[t_delta2-expected2]
- PASSED: test_concise_formatter_usetex[t_delta3-expected3]
- FAILED: test_date_formatter_usetex[delta2-expected2]
- FAILED: test_date_formatter_usetex[delta3-expected3]

**Issue**: AutoDateFormatter tests failing because `\;` (TeX thin space) being converted to regular space. Colons are correctly escaped.

**Analysis** (via codex volley): The issue is not in `_wrap_in_tex` but in `AutoDateFormatter`. It uses format strings from rcParams that contain regular spaces (e.g., `%m-%d %H`). When `usetex` is enabled, these spaces should be converted to `\;` for proper TeX spacing.

---

## Gate Loop - Iteration 3

**Trajectory**: Resolution

**Changes made**:
- `lib/matplotlib/dates.py:967-969` - Updated `AutoDateFormatter.__call__()`:
  - Added space-to-`\;` conversion when `self._usetex` is True
  - Applied before creating DateFormatter instance

**Gate result**: ✅ ALL TESTS PASS (77 passed)

**Summary of complete fix**:
1. `_wrap_in_tex()`: Escape colons as `{:}` (like dashes are escaped as `{-}`)
2. `AutoDateFormatter.__call__()`: Convert spaces to `\;` in format strings when usetex=True

Both changes are minimal and targeted. The recon diagnosis identified the colon escaping issue correctly but missed the space-to-`\;` conversion needed in AutoDateFormatter.


---

# Audit: matplotlib__matplotlib-21568

## FAIL_TO_PASS
- test_date_formatter_usetex[delta2-expected2]: ✅ PASS
- test_date_formatter_usetex[delta3-expected3]: ✅ PASS
- test_concise_formatter_usetex[t_delta2-expected2]: ✅ PASS
- test_concise_formatter_usetex[t_delta3-expected3]: ✅ PASS

## PASS_TO_PASS regressions
None - all 73 other tests continue to pass.

## Pre-existing (not counted, confirmed against base capture)
None - the baseline showed the delta2 and delta3 tests failing (which are now fixed).

## Patch summary
The craft patch modified two locations in `lib/matplotlib/dates.py`:
1. `_wrap_in_tex()` (line 598-599): Added `.replace(':', '{:}')` to escape colons in TeX math mode, matching the dash escaping behavior
2. `AutoDateFormatter.__call__()` (line 967-969): Added space-to-`\;` conversion for TeX thin spaces when usetex=True

Both changes are minimal, targeted, and address the root causes identified in recon. All 77 tests in the gate passed with zero regressions.

VERDICT: RESOLVED
RE-ENTER: none
