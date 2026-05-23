# Hypothesis graph: matplotlib__matplotlib-22871

## H₀ (abduction): Initial symptom
The test `test_offset_changes` fails with `AssertionError: assert '' == '1997'` when xlim spans weeks 7-30 (mid-Feb to late July 1997). The formatter returns an empty offset string instead of showing the year '1997'.

## H₁ (deduction): Root cause located
**File**: `lib/matplotlib/dates.py:800-801`

**Issue**: The condition `if level < 2: show_offset = False` suppresses the offset for both level 0 (years) and level 1 (months). This is incorrect for level 1 when January is NOT in the plot range.

**Why this is wrong**:
- When level=1 (months changing), tick labels show month names using `formats[1]='%b'` (e.g., 'Feb', 'Mar', 'Apr')
- The offset should show the year using `offset_formats[1]='%Y'` (e.g., '1997')
- The code assumes "year is already present in the axis" (per comment from commit 8996e1d7b2)
- This assumption holds when January is present, because January uses `zero_formats[1]='%Y'` to display the year
- But when January is NOT present, no tick displays the year, so the offset MUST show it
- Current code suppresses offset unconditionally for level < 2, causing the year to disappear entirely

**Supporting evidence**:
- `lib/matplotlib/dates.py:751-752`: `offset_formats = ['', '%Y', '%Y-%b', ...]` — level 1 is designed to show '%Y'
- `lib/matplotlib/dates.py:748`: `zero_formats[1] = '%Y'` (from formats[0]) — January shows the year
- `lib/matplotlib/dates.py:809`: `zerovals = [0, 1, 1, 0, 0, 0, 0]` — zerovals[1]=1 means January (month 1)
- Git history shows commit 8996e1d7b2 added this logic to avoid redundancy when January IS present, but didn't account for when it's absent

**Confidence**: deduction — 98% (traced the code path, verified with git history)

## Edit sites
`lib/matplotlib/dates.py:800-801` — Replace unconditional `if level < 2: show_offset = False` with conditional logic that checks whether January is present in the tick range when level=1. Specifically:
- For level 0 (years): always suppress offset (years appear in tick labels)
- For level 1 (months): only suppress offset if January (month 1) is present in tickdate[:, 1] (because January will show the year via zero_formats[1])

Implementation: Change from `if level < 2:` to `if level == 0 or (level == 1 and np.any(tickdate[:, 1] == 1)):`

## craft gate-loop node 1

**Iteration**: 1/8
**codex volley count**: 2

**Draft diff**:
```diff
--- a/lib/matplotlib/dates.py
+++ b/lib/matplotlib/dates.py
@@ -797,8 +797,8 @@ class ConciseDateFormatter(ticker.Formatter):
         # 3: hours, 4: minutes, 5: seconds, 6: microseconds
         for level in range(5, -1, -1):
             if len(np.unique(tickdate[:, level])) > 1:
-                if level < 2:
+                if level == 0 or (level == 1 and np.any(tickdate[:, 1] == 1)):
                     show_offset = False
                 break
             elif level == 0:
```

**codex feedback round 1**: Identified potential regression for multi-year month ticks without January. Suggested adding guard: `or len(np.unique(tickdate[:, 0])) > 1`

**codex feedback round 2** (on revised diff with multi-year guard): The multi-year guard creates a worse problem—for multi-year ticks without January, it suppresses the offset, resulting in NO year appearing anywhere (e.g., ['Dec', 'Feb', 'Apr'] with offset=''). Recommended the simpler fix without the guard—showing one year in the offset for multi-year cases is better than showing none. The minimal fix handles the failing test and doesn't break existing tests.

**Applied fix**: Simple January check only (without multi-year guard)

**Gate result**: ✅ PASSED (89/89 tests passed, including `test_offset_changes`)

**Trajectory**: Convergent-success (first gate run, all tests pass)

**Resolution**: The fix correctly handles:
- Single year, with January: offset suppressed (January label shows year)
- Single year, no January: offset shows year ✓ (fixes the failing test)
- Multi-year cases: offset shows year (better than no year)

# Audit: matplotlib__matplotlib-22871

## FAIL_TO_PASS
- lib/matplotlib/tests/test_dates.py::test_offset_changes: PASS ✅

## PASS_TO_PASS regressions
none

## Pre-existing (not counted, confirmed against base capture)
none

All 89 tests in test_dates.py passed. The FAIL_TO_PASS test now passes correctly, and all PASS_TO_PASS tests remain passing with zero regressions.

VERDICT: RESOLVED
RE-ENTER: none
