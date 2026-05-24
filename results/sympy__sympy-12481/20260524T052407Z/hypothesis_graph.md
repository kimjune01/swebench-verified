# Hypothesis graph: sympy__sympy-12481

## H₀: Overly restrictive duplicate check for cycle form

**Type**: Abduction → Deduction  
**Confidence**: 95% (deduction - traced code path and confirmed with manual testing)

**Observation**: Test fails with:
```
ValueError: there were repeated elements; to resolve cycles use Cycle(0, 1)(0, 2).
```
at `sympy/combinatorics/permutations.py:900`

**Root cause**: 
The constructor checks for duplicates in flattened cycle arguments (line 898-902) and raises ValueError when non-disjoint cycles are detected. However, this is overly restrictive because:

1. Non-disjoint cycles are mathematically valid (cycles can share elements)
2. The downstream code (lines 909-912) already handles cycle composition correctly:
   ```python
   c = Cycle()
   for ci in args:
       c = c(*ci)
   aform = c.list()
   ```
3. Manual testing confirms `Cycle()(0,1)(0,2).list()` produces `[1, 2, 0]`, matching `Permutation(0, 1, 2).array_form`

**Supporting evidence**:
- `permutations.py:897-902` - duplicate check blocks non-disjoint cycles before composition
- `permutations.py:909-912` - existing composition code that handles non-disjoint cycles correctly
- Manual test: `Cycle()(0,1)(0,2).list() == [1, 2, 0]` ✓
- Manual test: `Permutation(0, 1, 2).array_form == [1, 2, 0]` ✓

**Fix**: Remove the ValueError for `is_cycle` case at lines 899-901, or skip duplicate check entirely when `is_cycle` is True. The array form case (line 903) should still raise ValueError for duplicates.


## Craft iteration 1 (RESOLVED)

**Draft**: Removed the overly restrictive duplicate check for cycles (lines 899-901 in permutations.py). Changed the `if is_cycle: raise ValueError` branch to `if not is_cycle: raise ValueError`, allowing non-disjoint cycles to proceed to the composition logic below.

**Codex review**: Directionally correct. Main concern was whether duplicates within a single cycle would be handled correctly by Cycle composition, but noted the change allows the existing composition logic to handle non-disjoint cycles as intended.

**Gate result**: ✅ PASS - All 9 tests passed including test_args.

**Patch applied**:
```diff
--- a/sympy/combinatorics/permutations.py
+++ b/sympy/combinatorics/permutations.py
@@ -897,9 +897,7 @@ class Permutation(Basic):
 
         temp = flatten(args)
         if has_dups(temp):
-            if is_cycle:
-                raise ValueError('there were repeated elements; to resolve '
-                'cycles use Cycle%s.' % ''.join([str(tuple(c)) for c in args]))
-            else:
+            if not is_cycle:
                 raise ValueError('there were repeated elements.')
         temp = set(temp)
```

**Resolution**: FAIL_TO_PASS test now passes. The fix allows `Permutation([[0, 1], [0, 2]])` to proceed to cycle composition logic which correctly produces `Permutation(0, 1, 2)`.

---
## Audit: sympy__sympy-12481

### FAIL_TO_PASS
- test_args: **PASS** ✓

### PASS_TO_PASS
- test_Permutation: PASS ✓
- test_josephus: PASS ✓
- test_ranking: PASS ✓
- test_mul: PASS ✓
- test_Cycle: PASS ✓
- test_from_sequence: PASS ✓
- test_printing_cyclic: PASS ✓

### Regressions
None.

### Pre-existing failures
None.

### Gate output
All 9 tests passed. The patch successfully handles overlapping cycles by merging them, allowing `Permutation([[0, 1], [0, 2]])` to resolve to `Permutation(0, 1, 2)` instead of raising a ValueError.

