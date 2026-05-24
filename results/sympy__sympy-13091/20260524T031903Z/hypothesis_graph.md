# Hypothesis graph: sympy__sympy-13091

## H₀: Initial diagnosis (abduction, confidence: 85%)

**Symptom**: Tests `test_equality` and `test_comparisons_with_unknown_type` fail with AssertionError when comparing SymPy objects with unknown custom types.

**Root cause**: Rich comparison methods (__eq__, __ne__, __lt__, __le__, __gt__, __ge__) in SymPy classes return `False` or raise `TypeError` when they cannot understand the type of the other operand, instead of returning `NotImplemented` to delegate to the other object's reflected comparison method.

**Evidence**:
- `sympy/core/basic.py:316` - Basic.__eq__ returns False on SympifyError
- `sympy/core/basic.py:331` - Basic.__ne__ does `return not self.__eq__(other)` which fails when __eq__ returns NotImplemented
- `sympy/core/numbers.py:1261` - Float.__eq__ returns False on SympifyError
- `sympy/core/numbers.py:1278` - Float.__ne__ does `return not self.__eq__(other)`
- `sympy/core/numbers.py:1722` - Rational.__eq__ returns False on SympifyError
- `sympy/core/numbers.py:1736` - Rational.__ne__ does `return not self.__eq__(other)`
- `sympy/core/numbers.py:3342` - NumberSymbol.__eq__ returns False on SympifyError
- `sympy/core/numbers.py:3352` - NumberSymbol.__ne__ does `return not self.__eq__(other)`
- `sympy/core/expr.py:251,273,295,317` - Expr ordering methods raise TypeError on SympifyError
- `sympy/core/numbers.py` - Multiple Number subclasses' ordering methods raise TypeError on SympifyError

**Expected behavior**: When a SymPy object doesn't understand the other operand:
- Equality methods (__eq__, __ne__) should return NotImplemented
- Ordering methods (__lt__, __le__, __gt__, __ge__) should return NotImplemented
- Python will then try the reflected operation on the other object
- If both return NotImplemented, Python falls back to identity comparison for == and raises TypeError for ordering comparisons

**Test expectations**:
- `Bar.__eq__` returns True for any Basic instance
- When `b == bar` is evaluated (where b is Basic() and bar is Bar()):
  - Basic.__eq__ should return NotImplemented (doesn't understand Bar)
  - Python delegates to Bar.__eq__(b), which returns True
  - Result: `b == bar` is True (symmetric with `bar == b`)


## Edit site enumeration (complete list)

### Tier 1: Critical for passing test_equality and test_comparisons_with_unknown_type

**__eq__ methods - change `return False` to `return NotImplemented`:**
1. `basic.py:316` - Basic.__eq__
2. `numbers.py:1261` - Float.__eq__
3. `numbers.py:1722` - Rational.__eq__
4. `numbers.py:3342` - NumberSymbol.__eq__

**__ne__ methods - change `return not self.__eq__(other)` to handle NotImplemented:**
5. `basic.py:331` - Basic.__ne__
6. `numbers.py:1278` - Float.__ne__
7. `numbers.py:1736` - Rational.__ne__
8. `numbers.py:2114` - Integer.__ne__
9. `numbers.py:3352` - NumberSymbol.__ne__

**Expr ordering methods - change `raise TypeError` to `return NotImplemented`:**
10. `expr.py:251` - Expr.__ge__
11. `expr.py:273` - Expr.__le__
12. `expr.py:295` - Expr.__gt__
13. `expr.py:317` - Expr.__lt__

**Float ordering methods - change `raise TypeError` to `return NotImplemented`:**
14. `numbers.py:1284` - Float.__gt__
15. `numbers.py:1298` - Float.__ge__
16. `numbers.py:1312` - Float.__lt__
17. `numbers.py:1326` - Float.__le__

**Rational ordering methods - change `raise TypeError` to `return NotImplemented`:**
18. `numbers.py:1742` - Rational.__gt__
19. `numbers.py:1760` - Rational.__ge__
20. `numbers.py:1778` - Rational.__lt__
21. `numbers.py:1796` - Rational.__le__

**Integer ordering methods - change `raise TypeError` to `return NotImplemented`:**
22. `numbers.py:2120` - Integer.__gt__
23. `numbers.py:2129` - Integer.__lt__
24. `numbers.py:2138` - Integer.__ge__
25. `numbers.py:2147` - Integer.__le__

**Infinity ordering methods - change `raise TypeError` to `return NotImplemented`:**
26. `numbers.py:2842` - Infinity.__lt__
27. `numbers.py:2851` - Infinity.__le__
28. `numbers.py:2865` - Infinity.__gt__
29. `numbers.py:2879` - Infinity.__ge__

**NegativeInfinity ordering methods - change `raise TypeError` to `return NotImplemented`:**
30. `numbers.py:3063` - NegativeInfinity.__lt__
31. `numbers.py:3077` - NegativeInfinity.__le__
32. `numbers.py:3086` - NegativeInfinity.__gt__
33. `numbers.py:3095` - NegativeInfinity.__ge__

**NumberSymbol ordering methods - change `raise TypeError` to `return NotImplemented`:**
34. `numbers.py:3356` - NumberSymbol.__lt__
35. `numbers.py:3377` - NumberSymbol.__le__
36. `numbers.py:3390` - NumberSymbol.__gt__
37. `numbers.py:3401` - NumberSymbol.__ge__

### Tier 2: Consistency improvements (not required for current tests)

**Special number __eq__/__ne__ - change identity checks to return NotImplemented for non-identity:**
- `numbers.py:2833-2836` - Infinity.__eq__/__ne__ (currently `return other is/is not S.Infinity`)
- `numbers.py:3054-3057` - NegativeInfinity.__eq__/__ne__ (currently `return other is/is not S.NegativeInfinity`)
- `numbers.py:3219-3223` - NaN.__eq__/__ne__ (currently `return other is/is not S.NaN`)

These could return NotImplemented when `other is not <self-singleton>` to allow custom types to claim equality with these singletons.

**Base class ordering methods:**
- `numbers.py:700,708,716,723` - Number base class __lt__/__le__/__gt__/__ge__ (raises NotImplementedError after catching SympifyError, but could return NotImplemented first)

Total: 37 required changes, 7 optional consistency improvements

## Craft gate loop 1: Infinite recursion (divergent)

**Changes applied**:
1. Basic.__eq__: return NotImplemented in SympifyError handler ✓
2. Basic.__ne__: handle NotImplemented from __eq__ ✓  
3. Expr ordering methods (4): return NotImplemented in SympifyError handler ✓
4. Number subclass ordering methods (24): return NotImplemented in SympifyError handler ✓
5. Number subclass __ne__ methods (4): handle NotImplemented ✓
6. Number subclass __eq__ methods (3: Float, Rational, NumberSymbol): return NotImplemented in SympifyError handler - **CAUSES INFINITE RECURSION**

**Gate result**: Infinite recursion through sympify.py line 244 `if a in sympy_classes:`

**Root cause** (from codex analysis):
- Rational.__eq__ calls `_sympify(other)`  
- sympify does `if a in sympy_classes:` membership check
- This calls `Rational.__eq__` with class objects
- When we return NotImplemented, Python tries reflected comparison
- This re-enters sympify, creating infinite loop

**Solution needed**: 
Add `isinstance(other, type)` check in Number subclass __eq__ methods BEFORE calling _sympify to break the loop while still returning NotImplemented for unknown non-class objects.

The fix requires modifying Float.__eq__, Rational.__eq__, and NumberSymbol.__eq__ to:
```python
def __eq__(self, other):
    # Break sympify loop - can't be equal to a class object
    if isinstance(other, type):
        return False
    try:
        other = _sympify(other)
    except SympifyError:
        return NotImplemented  # Delegate to other's __eq__
    # ... rest of method
```

## Craft conclusion (iteration 1, multiple attempts)

**Status**: NOT-RESOLVED after 1 gate iteration with multiple fix attempts

**Issue**: The straightforward implementation of "return NotImplemented in SympifyError handlers" causes infinite recursion through sympify's membership checks. The type guard `isinstance(other, type)` was added to break the loop, but recursion persists.

**Attempted fixes**:
1. Direct NotImplemented in SympifyError handlers → infinite recursion
2. Added `isinstance(other, type)` guard → still infinite recursion

**Analysis**: The recursion mechanism is more complex than anticipated. Simply returning NotImplemented from Number subclass __eq__ methods creates a loop that the type check alone doesn't break.

**Recommendation**: The recon diagnosis correctly identified the WHAT (need NotImplemented), but the implementation strategy needs refinement. Possible approaches:
1. Modify sympify.py to avoid __eq__ calls in membership checks
2. Use a different strategy for Number subclasses vs Basic
3. Re-diagnose to find if there's a simpler solution that avoids the sympify loop entirely

The working tree has:
- Basic.__eq__: returns NotImplemented ✓
- Basic.__ne__: handles NotImplemented ✓
- All ordering methods: return NotImplemented ✓
- All __ne__ methods: handle NotImplemented ✓
- Number subclass __eq__: attempts NotImplemented but causes infinite loop

## H2: Sympify recursion + missing NotImplemented returns (abduction - 75%)

**Observation:** Prior fix changed comparison methods to return NotImplemented on SympifyError, but introduced two new issues:

1. **Recursion in sympify membership check**: When comparing `Integer == S.NaN`, Rational.__eq__ calls `_sympify(S.NaN)`, which does `if a in sympy_classes` (line 244), triggering NaN.__hash__() during the membership test. This creates infinite recursion when already deep in comparison/sympify call stacks.

2. **Final fallback returns False instead of NotImplemented**: After successfully sympifying to a Basic object of different type, several __eq__ methods return `False` instead of `NotImplemented`:
   - `Basic.__eq__` line 318: `return False` after types don't match post-sympify
   - `Float.__eq__` line 1279: `return False # Float != non-Number`
   - `Rational.__eq__` line 1740: `return False`
   - `NumberSymbol.__eq__` line 3360: `return False # NumberSymbol != non-(Number|self)`

**Evidence:**
- Stack trace shows `isinstance(p, fractions.Fraction)` in Rational.__new__ → ABC.__instancecheck__ → recursion
- But deeper root: `if S.NaN in (b, e)` in power.py:207 → Integer.__eq__(b, S.NaN) → Rational.__eq__ → `_sympify(S.NaN)` → `if a in sympy_classes` → NaN.__hash__() → recursion
- test_NumberSymbol_comparison fails: `(rpi > pi) != (pi < rpi)` - asymmetric comparisons
- test_equality and test_comparisons_with_unknown_type pass in isolation

**Root cause:**
1. **Recursion**: Number subclass __eq__ methods call `_sympify(other)` without first checking if `other` is already a Basic instance. When `other` is a SymPy singleton like S.NaN, sympify's membership check `if a in sympy_classes` triggers __hash__/__eq__ again.
2. **NotImplemented propagation**: After sympify succeeds but types don't match, returning False prevents the other object's __eq__ from being tried.

**Fix locations:**
- `sympy/core/numbers.py`:
  - Rational.__eq__ (1724-1740): Add `isinstance(other, Basic)` check before sympify
  - Float.__eq__ (1249-1279): Add `isinstance(other, Basic)` check; change final `return False` to `return NotImplemented`
  - NumberSymbol.__eq__ (3350-3360): Add `isinstance(other, Basic)` check; change final `return False` to `return NotImplemented`
  - Infinity.__eq__ (2845): Try sympify first, return NotImplemented for unknown types
  - NegativeInfinity.__eq__ (3066): Try sympify first, return NotImplemented for unknown types
  - NaN.__eq__ (3231): Try sympify first, return NotImplemented for unknown types
- `sympy/core/basic.py`:
  - Basic.__eq__ line 318: Change `return False` to `return NotImplemented`

**Confidence:** Abduction - 75% (traced recursion to sympify membership check; final False returns violate NotImplemented protocol)

## Gate Loop - Iteration 1

Attempt: Added `isinstance(other, Basic)` check before sympify in all Number.__eq__ methods

Result: Different recursion in `isinstance(p, fractions.Fraction)` check in Rational.__new__

```
RecursionError: maximum recursion depth exceeded in comparison
  File "/testbed/sympy/core/numbers.py", line 1481, in __new__
    if isinstance(p, fractions.Fraction):
  File "/opt/miniconda3/envs/testbed/lib/python3.9/abc.py", line 119, in __instancecheck__
    return _abc_instancecheck(cls, instance)
```

## Gate Loop - Iteration 2 

Attempt: Removed isinstance(Basic) check, only changed SympifyError return from False to NotImplemented

Result: Original recursion persists

```
RecursionError at power.py:207 if S.NaN in (b, e)
→ Integer.__eq__(S.NaN) → Rational.__eq__ → _sympify(S.NaN)  
→ sympify checks `if S.NaN in sympy_classes` → NaN.__hash__() → recursion
```

Evidence: The isinstance(Basic) check is necessary to prevent sympify recursion, but it itself triggers recursion through ABCMeta isinstance checks.

**Hypothesis stuck after 2 iterations**: The fix needs isinstance(Basic) to avoid sympify recursion, but isinstance itself causes recursion. Need a different guard condition.

## H2: Wrong reflection method mapping (CURRENT)

**Status**: Active diagnosis (recon iteration 2)

**Observation**: The test `test_NumberSymbol_comparison` fails with:
```
assert (rpi > pi) == (pi < rpi)
AssertionError
```

Where `rpi > pi` returns `True` but `pi < rpi` returns `False`.

**Root cause**: Float and Rational classes manually implement comparison method reflection (calling the reflected method on the other object when it's a NumberSymbol), but use the WRONG method mappings:

Current (WRONG):
- `Float.__gt__` (line 1292) calls `other.__le__` — should call `other.__lt__`
- `Float.__ge__` (line 1306) calls `other.__lt__` — should call `other.__le__`  
- `Float.__lt__` (line 1320) calls `other.__ge__` — should call `other.__gt__`
- `Float.__le__` (line 1334) calls `other.__gt__` — should call `other.__ge__`
- `Rational.__gt__` (line 1755) calls `other.__le__` — should call `other.__lt__`
- `Rational.__ge__` (line 1773) calls `other.__lt__` — should call `other.__le__`
- `Rational.__lt__` (line 1791) calls `other.__ge__` — should call `other.__gt__`
- `Rational.__le__` (line 1810) calls `other.__gt__` — should call `other.__ge__`

Python's reflection protocol maps:
- `__gt__` ↔ `__lt__` (not `__le__`)
- `__ge__` ↔ `__le__` (not `__lt__`)
- `__lt__` ↔ `__gt__` (not `__ge__`)
- `__le__` ↔ `__ge__` (not `__gt__`)

**Evidence**: When comparing `rpi > pi` where rpi is Rational and pi is NumberSymbol:
1. `Rational.__gt__(rpi, pi)` calls `pi.__le__(rpi)` (wrong - should call `__lt__`)
2. `NumberSymbol.__le__` compares `pi.evalf() <= rpi` → `3.14159... <= Rational(...)` → True

When comparing `pi < rpi`:
1. `NumberSymbol.__lt__(pi, rpi)` compares `pi.evalf() < rpi` → `3.14159... < Rational(...)` → False

The use of `<=` vs `<` on float-precision-equal values gives different results.

**Confidence**: deduction — 98%

**Edit sites**:
- `sympy/core/numbers.py` lines 1292, 1306, 1320, 1334 (Float class)
- `sympy/core/numbers.py` lines 1755, 1773, 1791, 1810 (Rational class)  
- Change each reflected method call to use the correct mapping per Python's protocol

**Secondary issue**: Comparison methods raise `TypeError` on `SympifyError` instead of returning `NotImplemented`, preventing proper delegation. This affects:
- All `__lt__`, `__le__`, `__gt__`, `__ge__` methods in Number subclasses
- Should return `NotImplemented` instead of `raise TypeError`


## Audit - Iteration 1

**Patch status**: Live in tree (3 files, +33/-25 lines)

**Gate results**:
- 93 passed
- 1 failed: test_comparisons_with_unknown_type (AssertionError line 1702)
- 1 expected to fail
- 3 exceptions (including test_equality RecursionError)

**FAIL_TO_PASS classification**:
- test_equality: RecursionError (pre-existing - fail-on-base shows identical pattern)
- test_comparisons_with_unknown_type: Still fails (fix was ineffective)

**PASS_TO_PASS classification**:
- No regressions (93 passed)

**Pre-existing failures**:
- test_equality RecursionError confirmed in fail-on-base

**Root cause of failure**: Incomplete fix. The patch changed:
- ✓ Basic.__eq__ returns NotImplemented
- ✓ Basic.__ne__ handles NotImplemented
- ✓ Expr comparison operators return NotImplemented
- ✓ Number comparison operator reflection mapping fixes
- ✓ All __ne__ methods handle NotImplemented
- ✗ Number subclass __eq__ methods (Rational, Float, NumberSymbol) still return False

The test `test_comparisons_with_unknown_type` line 1702 expects `Integer(3) == bar` to delegate to `bar.__eq__(Integer(3))` when Rational.__eq__ can't sympify bar. But Rational.__eq__ returns False instead of NotImplemented, breaking the reflection protocol.

Per hypothesis graph, craft iteration 1 attempted this fix but encountered infinite recursion through sympify's `if a in sympy_classes` membership check. Rather than resolve the recursion, craft backed out the Number.__eq__ changes, leaving only Basic.__eq__ and comparison operators fixed.

**Verdict**: NOT_RESOLVED — fix ineffective  
**Route**: RE-ENTER: recon (diagnosis missed the sympify recursion blocker)
