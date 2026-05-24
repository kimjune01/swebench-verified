# Hypothesis graph: sympy__sympy-20154

## H₀: Dictionary reuse in partitions() causes test failures (abduction → deduction)
**Status:** Root cause identified
**Confidence:** 99% (deduction - traced code execution path)
**Date:** 2026-05-23

### Failure symptom
- `test_partitions` fails: `[p for p in partitions(6, k=2)]` returns `[{1: 6}, {1: 6}, {1: 6}, {1: 6}]`
- Expected: `[{2: 3}, {1: 2, 2: 2}, {1: 4, 2: 1}, {1: 6}]`
- `test_uniq` fails: `list(uniq(p for p in partitions(4)))` returns `[{1: 4}]`
- Expected: `[{4: 1}, {1: 1, 3: 1}, {2: 2}, {1: 2, 2: 1}, {1: 4}]`

### Root cause
The `partitions()` iterator reuses the same dictionary object (`ms`) across all iterations:
1. Creates single `ms` dict at line 1796
2. Modifies `ms` in-place throughout the while loop (lines 1810-1848)
3. Yields `ms` directly without copying at lines 1807 and 1847
4. Result: all yielded values point to the same object, which ends with the final partition value

### Evidence
- `sympy/utilities/iterables.py:1807` - `yield ms` (no copy)
- `sympy/utilities/iterables.py:1847` - `yield ms` (no copy)
- Verified by running: `[p for p in partitions(6, k=2)]` → all 4 elements are same object with value `{1: 6}`
- Docstring acknowledges this behavior but new tests require it fixed

### Edit sites
Four yield statements must copy the dictionary before yielding:
- Line 1805: `yield sum(ms.values()), ms` → `yield sum(ms.values()), ms.copy()`
- Line 1807: `yield ms` → `yield ms.copy()`
- Line 1845: `yield sum(ms.values()), ms` → `yield sum(ms.values()), ms.copy()`
- Line 1847: `yield ms` → `yield ms.copy()`

Note: Empty partition cases (lines 1777, 1787) yield new dict literals, not affected.

## Gate loop: craft iteration 1

**Volley with codex:** Reviewed proposed diff adding `.copy()` to all four yield statements. Codex confirmed: "No correctness problem in the proposed diff. Copying `ms` at every yield is the right fix."

**Applied changes:**
- Line 1805: `yield sum(ms.values()), ms` → `yield sum(ms.values()), ms.copy()`
- Line 1807: `yield ms` → `yield ms.copy()`
- Line 1845: `yield sum(ms.values()), ms` → `yield sum(ms.values()), ms.copy()`
- Line 1847: `yield ms` → `yield ms.copy()`

**Gate result:** ✅ PASS - All 43 tests passed (0.28 seconds)
- `test_partitions` ✅
- `test_uniq` ✅

**Resolution:** First-iteration success. The fix addresses the root cause exactly as diagnosed by recon.

---

# Audit: sympy__sympy-20154

## FAIL_TO_PASS
- `test_partitions`: **PASS** ✓
- `test_uniq`: **PASS** ✓

## PASS_TO_PASS regressions
None. All 41 PASS_TO_PASS tests remain passing.

## Pre-existing failures (not counted)
None confirmed against base capture.

## Verdict
All FAIL_TO_PASS tests now pass, zero regressions introduced. The patch successfully fixes the dictionary reuse bug in `partitions()` by adding `.copy()` to all four yield statements, ensuring each yielded partition is an independent object.

VERDICT: RESOLVED
RE-ENTER: none
