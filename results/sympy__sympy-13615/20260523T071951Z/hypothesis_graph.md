# Hypothesis graph: sympy__sympy-13615

## H₀ - Initial Observation (abduction)
**Timestamp**: Initial recon pass
**Status**: Root cause identified

The test `test_Complement` fails with AssertionError at line 191:
```
assert Complement(FiniteSet(x, y, 2), Interval(-10, 10)) == \
        Complement(FiniteSet(x, y), Interval(-10, 10))
```

**Actual behavior**: `Complement(FiniteSet(x, y, 2), Interval(-10, 10))` evaluates to `{x, y}`
**Expected behavior**: Should evaluate to `{x, y} \ Interval(-10, 10)` (unevaluated Complement)

The issue is that when computing the complement, the number 2 is correctly removed (since 2 ∈ [-10,10]), but the Complement wrapper is also incorrectly discarded for the symbolic elements x and y.

## H₁ - Root Cause (deduction, 95%)
**File**: `sympy/sets/sets.py`
**Suspect lines**: 994-1006 (Interval._complement) and 188-220 (Set._complement)

The bug is in how `Interval._complement` handles mixed FiniteSet (containing both numeric and symbolic elements):

**Current logic** (lines 1002-1006):
```python
if isinstance(other, FiniteSet):
    nums = [m for m in other.args if m.is_number]
    if nums == []:
        return None  # Preserves Complement for pure symbolic case
    # Falls through to Set._complement for mixed case
return Set._complement(self, other)
```

Then in `Set._complement` (line 220):
```python
elif isinstance(other, FiniteSet):
    return FiniteSet(*[el for el in other if self.contains(el) != True])
```

**The problem**: The condition `self.contains(el) != True` treats three cases the same:
1. `contains(el) == False` (element definitely NOT in interval) → keep ✓
2. `contains(el) == symbolic` (uncertain if element is in interval) → keep ✗
3. `contains(el) == True` (element definitely in interval) → remove ✓

For case 2 (symbolic elements), the result should remain as a Complement, not a plain FiniteSet.

**Evidence**:
- `Interval(-10,10).contains(2)` returns `True` (BooleanTrue)
- `Interval(-10,10).contains(15)` returns `False` (BooleanFalse)  
- `Interval(-10,10).contains(x)` returns `(x >= -10) & (x <= 10)` (symbolic And expression)

The filter `self.contains(el) != True` keeps both case 1 and case 2, collapsing symbolic uncertainty into a concrete FiniteSet.

## Edit Sites

**Primary fix location**: `sympy/sets/sets.py`, lines 1002-1006 (Interval._complement)

Need to handle FiniteSet with mixed numeric/symbolic elements by:
1. Partitioning elements into three groups based on `self.contains(el)`:
   - `== True`: definitely in interval (remove entirely)
   - `== False`: definitely not in interval (keep in FiniteSet)
   - neither: uncertain (keep in Complement)
2. Return Union of:
   - FiniteSet of definitely-not-in elements (if any)
   - Complement(FiniteSet of uncertain elements, self) (if any)
   - EmptySet if both groups are empty

**Alternative approach**: Could fix in `Set._complement` at line 220, but Interval-specific handling is cleaner since intervals have well-defined containment semantics.

## Supporting Evidence

**Test trace**:
```python
>>> Complement(FiniteSet(2, 3, 15), Interval(-10, 10))
{15}  # ✓ correct: pure numeric, removes 2,3 keeps 15

>>> Complement(FiniteSet(x, y), Interval(-10, 10))  
{x, y} \ Interval(-10, 10)  # ✓ correct: pure symbolic, preserves Complement

>>> Complement(FiniteSet(x, y, 2), Interval(-10, 10))
{x, y}  # ✗ incorrect: mixed, should be {x, y} \ Interval(-10, 10)
```

The pure-symbolic case works because `nums == []` triggers early return None.
The mixed case fails because nums is non-empty, falls through to Set._complement, which over-simplifies.


## Craft Gate Loop

### Iteration 1: Initial implementation

**Hypothesis**: Interval._complement needs to partition FiniteSet elements into three categories based on contains() results: definitely in (True), definitely out (False), and uncertain (symbolic).

**Implementation**: Modified Interval._complement to:
1. Check self.contains(el) for each element
2. Partition into definitely_in, definitely_out, uncertain lists
3. Return Union of FiniteSet(*definitely_out) and Complement(FiniteSet(*uncertain), self, evaluate=False)

**Pre-gate codex review**: Identified critical issue - must use `is S.true` and `is S.false` instead of `is True` and `is False` because SymPy's contains() returns BooleanTrue/BooleanFalse, not Python bool.

**Gate result**: FAILED - test still failed because boolean checks used `is True`/`is False`

### Iteration 2: Fixed boolean type checks

**Revision**: Changed boolean identity checks from Python built-ins to SymPy singletons:
- `contains_result is True` → `contains_result is S.true`
- `contains_result is False` → `contains_result is S.false`

**Gate result**: PASSED ✓

All 72 tests passed including test_Complement. The fix correctly:
- Excludes numeric elements definitely in the interval (e.g., 2 in [-10, 10])
- Keeps numeric elements definitely not in the interval as plain FiniteSet
- Preserves symbolic elements (x, y) in an unevaluated Complement expression

**E-value**: Convergent (oscillatory → green) - fixed boolean type check resolved the issue

**Resolution**: RESOLVED - FAIL_TO_PASS test now passes

---

## Audit Verification
**Timestamp**: Final verification on patched code
**Status**: RESOLVED

### FAIL_TO_PASS Results
- `test_Complement`: **PASS** ✓
  - Baseline: F (failing)
  - Patched: ok (passing)
  - The fix successfully resolves the issue

### PASS_TO_PASS Analysis
**Total PASS_TO_PASS tests checked**: 71
**Regressions**: None

All PASS_TO_PASS tests remain passing:
- test_imageset, test_interval_arguments, test_interval_symbolic_end_points
- test_union, test_union_iter, test_difference, test_complement
- test_intersect, test_intersection, test_issue_9623, test_is_disjoint
- test_ProductSet_of_single_arg_is_arg, test_interval_subs
- test_interval_to_mpi, test_measure, test_is_subset
- test_is_proper_subset, test_is_superset, test_is_proper_superset
- test_contains, test_interval_symbolic, test_union_contains
- test_is_number, test_Interval_is_left_unbounded
- test_Interval_is_right_unbounded, test_Interval_as_relational
- test_Finite_as_relational, test_Union_as_relational
- test_Intersection_as_relational, test_EmptySet, test_finite_basic
- test_powerset, test_product_basic, test_real, test_supinf
- test_universalset, test_Union_of_ProductSets_shares
- test_Interval_free_symbols, test_image_interval, test_image_piecewise
- test_image_FiniteSet, test_image_Union, test_image_EmptySet
- test_issue_5724_7680, test_boundary, test_boundary_Union
- test_boundary_ProductSet, test_boundary_ProductSet_line
- test_is_open, test_is_closed, test_closure, test_interior
- test_issue_7841, test_Eq, test_SymmetricDifference
- test_issue_9536, test_issue_9637, test_issue_9808, test_issue_9956
- test_issue_Symbol_inter, test_issue_11827, test_issue_10113
- test_issue_10248, test_issue_9447, test_issue_10337
- test_issue_10326, test_issue_2799, test_issue_9706
- test_issue_8257, test_issue_10931, test_issue_11174

### Pre-existing failures (not counted)
- `test_image_Intersection`: f (expected fail in both baseline and patched)
- `test_union_boundary_of_joining_sets`: f (expected fail in both baseline and patched)

These are marked as expected failures and are not regressions.

### Summary
The patch successfully fixes the Complement evaluation issue for mixed symbolic/numeric FiniteSets without introducing any regressions. The fix correctly partitions elements based on their definite membership status in the interval and preserves symbolic uncertainty in an unevaluated Complement expression.

**Final gate**: 72 passed, 2 expected to fail, in 47.23 seconds
