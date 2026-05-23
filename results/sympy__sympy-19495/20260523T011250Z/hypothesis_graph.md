# Hypothesis graph: sympy__sympy-19495

---

## Hypothesis Node: Initial Diagnosis

**Timestamp**: 2026-05-22 (recon phase)
**Status**: Active hypothesis
**Reasoning mode**: Deduction
**Confidence**: 98%

### Problem

When substituting a free variable in a ConditionSet's condition, if the condition evaluates to `True`, the `_eval_subs` method incorrectly creates a new ConditionSet with the substituted value (not a symbol) as the dummy variable, instead of returning the base set.

### Root cause

`sympy/sets/conditionset.py:246` in the `_eval_subs` method:
```python
if cond is S.true:
    return ConditionSet(new, Contains(new, base), base)
```

This line creates a malformed ConditionSet when `new` is not a symbol (e.g., `Rational(1, 3)`). When the condition is `True`, every element in the base set satisfies it, so the ConditionSet should reduce to just the base set.

### Evidence

1. Reproduction: `ConditionSet(x, Contains(y, Interval(-1,1)), img1).subs(y, 1/3)` produces `ConditionSet(1/3, Contains(1/3, ImageSet(...)), ImageSet(...))` instead of just `ImageSet(...)`

2. Consistency with `__new__`: Lines 146-147 in `__new__` already handle this correctly:
   ```python
   elif condition is S.true:
       return base_set
   ```

3. Git blame shows line 246 was added in commit e38f40340a6 (2018-03-19) as part of "increase safety of ConditionSet" but contains a logic error

### Proposed fix

Change line 246 from:
```python
return ConditionSet(new, Contains(new, base), base)
```
to:
```python
return base
```

### Test coverage

The failing test `test_subs_CondSet` specifically checks this case with issue #17341.


## Craft Phase - Gate Loop

### Iteration 1: Initial Fix Applied
**Change**: Line 246 in `sympy/sets/conditionset.py`
- **Before**: `return ConditionSet(new, Contains(new, base), base)`
- **After**: `return base`

**Rationale**: When `cond is S.true` after substitution, the condition no longer filters the base set, so we should return the base set directly. This matches the pattern in `__new__` (lines 146-147) where `condition is S.true` returns `base_set`.

**Gate Result**: ✅ PASS
- All 9 tests passed
- `test_subs_CondSet` now passes
- 1 expected failure (test_failing_contains) as designed

**Trajectory**: Convergent success - first attempt resolved the issue.


---

## Audit Phase

**Timestamp**: 2026-05-22

### Gate Execution Results

All tests passed successfully:

**FAIL_TO_PASS:**
- test_subs_CondSet: ✅ PASS (was FAIL on base, now fixed)

**PASS_TO_PASS:**
- test_CondSet: ✅ ok
- test_CondSet_intersect: ✅ ok
- test_issue_9849: ✅ ok
- test_simplified_FiniteSet_in_CondSet: ✅ ok
- test_free_symbols: ✅ ok
- test_subs_CondSet_tebr: ✅ ok
- test_dummy_eq: ✅ ok
- test_contains: ✅ ok

**Pre-existing failures (not counted):**
- test_failing_contains: f (expected to fail, confirmed on base)

### Regression Analysis

**Regressions:** none

All PASS_TO_PASS tests maintained their passing status. No regressions introduced.

### Patch Verification

```diff
diff --git a/sympy/sets/conditionset.py b/sympy/sets/conditionset.py
index 118eda6f77..c8c70929d9 100644
--- a/sympy/sets/conditionset.py
+++ b/sympy/sets/conditionset.py
@@ -243,7 +243,7 @@ def _eval_subs(self, old, new):
         cond = self.condition.subs(old, new)
         base = self.base_set.subs(old, new)
         if cond is S.true:
-            return ConditionSet(new, Contains(new, base), base)
+            return base
         return self.func(self.sym, cond, cond, base)
```

The fix correctly returns the base set when the condition evaluates to `True` after substitution, which is the mathematically correct behavior (a condition that's always true doesn't filter the set).

### Final Classification

- ✅ All FAIL_TO_PASS tests pass
- ✅ Zero PASS_TO_PASS regressions
- ✅ Patch is minimal and correct

