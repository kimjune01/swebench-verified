# Hypothesis graph: sympy__sympy-19954

## H₀: Baseline symptom (abduction, 60%)
The test `test_sylow_subgroup` fails when calling `G.sylow_subgroup(p=2)` on `DihedralGroup(18)` and `DihedralGroup(50)`. The error is:
```
IndexError: list assignment index out of range
```
at `sympy/combinatorics/perm_groups.py:2201` in the `minimal_blocks()` method:
```python
del num_blocks[i], blocks[i]
```

## H₁: Index misalignment in minimal_blocks (deduction, 99%)

**Root cause**: The `minimal_blocks` function maintains three parallel lists (`blocks`, `num_blocks`, `rep_blocks`) but has an index misalignment bug when removing non-minimal block systems.

**Code path**:
1. `sylow_subgroup()` at line 4354 calls `self.minimal_blocks()`
2. `minimal_blocks()` iterates over orbits of the stabilizer
3. For each orbit, it checks if new block systems are minimal compared to already-discovered ones
4. When a previously-discovered system is found to be non-minimal, it should be removed from all three parallel lists
5. The bug: at line 2201, the code deletes from `blocks[i]` and `num_blocks[i]` inside a loop that enumerates `rep_blocks`
6. After each deletion, `blocks` and `num_blocks` shrink, but `i` continues to increment based on the original `rep_blocks` enumeration
7. Eventually `i` exceeds the current length of `blocks` and `num_blocks`, causing `IndexError`

**Supporting evidence**:
- `perm_groups.py:2194-2206` — The loop iterates with `for i, r in enumerate(rep_blocks):` and deletes from `blocks[i]` and `num_blocks[i]` immediately, but defers removal from `rep_blocks` using `to_remove` list and filtering afterwards
- `perm_groups.py:2201` — `del num_blocks[i], blocks[i]` modifies the lists during iteration
- `perm_groups.py:2208` — `rep_blocks = [r for r in rep_blocks if r not in to_remove]` shows the correct pattern for deferred removal
- Git history (commit 19285f5a077, Aug 2017) — Bug has existed since the function was first introduced

**Fix specification**: Defer deletions from `blocks` and `num_blocks` to after the loop, matching the pattern already used for `rep_blocks`. Collect indices to remove, then filter all three lists consistently.

**Confidence**: Deduction (99%) — The bug is directly observable in the code structure and reproducible.

## Craft Gate Loop

### Iteration 1: Applied deferred-removal fix

**Change**: Modified `minimal_blocks` function in `sympy/combinatorics/perm_groups.py` (lines 2197-2210):
- Changed `to_remove.append(rep_blocks[i])` to `to_remove.append(i)` - collect indices instead of values
- Removed immediate deletion `del num_blocks[i], blocks[i]` from inside the loop
- Replaced single `rep_blocks` filter with three parallel filters that apply deferred removal to all three lists (`blocks`, `num_blocks`, `rep_blocks`)

**Gate result**: ✅ PASS
- `test_sylow_subgroup` now passes
- All 58 tests passed, 1 skipped, 2 expected failures
- No regressions

**Status**: RESOLVED

---

# Audit: sympy__sympy-19954

## FAIL_TO_PASS
- test_sylow_subgroup: ✅ **PASS** (was IndexError on base, now passes)

## PASS_TO_PASS regressions
**None** - all PASS_TO_PASS tests continue to pass.

## Pre-existing failures (not counted, confirmed against base capture)
- test_rubik: f (expected to fail)
- test_subgroup_search2: f (expected to fail)
- test_presentation: Slow w (warning)

## Audit Verdict
✅ **RESOLVED** - The fix successfully corrected the IndexError in `minimal_blocks()` by implementing deferred removal for all three parallel lists (`blocks`, `num_blocks`, `rep_blocks`). The test `test_sylow_subgroup` now passes, and no PASS_TO_PASS tests regressed.

VERDICT: RESOLVED
RE-ENTER: none
