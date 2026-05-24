# Hypothesis graph: sympy__sympy-12489

## Hypothesis Node: H0-baseline
**Type**: Abduction
**Timestamp**: Initial diagnosis
**Status**: Active

The test `test_Permutation_subclassing` fails at line 251:
```python
assert type(p * q) == CustomPermutation
AssertionError
```

where `p = CustomPermutation([1, 2, 3, 0])` and `q = Permutation([1, 2, 3, 0])`.

The test expects that when a `CustomPermutation` instance is multiplied by another permutation, the result should be a `CustomPermutation`, but it's returning a `Permutation` instead.

**Evidence**:
- Test failure output shows `AssertionError` at line 251
- The test creates a subclass `CustomPermutation` and expects operations to preserve the subclass type

## Hypothesis Node: H1-root-cause
**Type**: Deduction
**Timestamp**: After code inspection
**Status**: Active
**Confidence**: 95%

**Root Cause**: The `Permutation._af_new` static method hard-codes the class as `Perm` (which is an alias for `Permutation`) instead of accepting a class parameter. This causes all operations that create new permutation instances to return `Permutation` objects rather than preserving the subclass type.

**Code Path**:
1. `p * q` calls `p.__mul__(q)` (CustomPermutation inherits `__mul__` from Permutation)
2. `Permutation.__mul__` at line 1303 returns `_af_new(perm)`
3. `_af_new` is defined at module level (line 2831) as `Perm._af_new`
4. `Perm._af_new` at line 947 creates instance with `Basic.__new__(Perm, perm)` 
5. This always returns a `Permutation` instance, ignoring the actual class of `self`

**Supporting Evidence**:
- `sympy/combinatorics/permutations.py:927-950` - `_af_new` is a `@staticmethod` that hard-codes `Perm`
- `sympy/combinatorics/permutations.py:947` - `p = Basic.__new__(Perm, perm)` uses `Perm` not a class parameter
- `sympy/combinatorics/permutations.py:2831` - Module-level `_af_new = Perm._af_new`
- `sympy/combinatorics/permutations.py:1303` - `__mul__` returns `_af_new(perm)` without class context
- `sympy/combinatorics/permutations.py:860,862,870,872` - `__new__` uses `_af_new` instead of `cls._af_new`

**Additional affected methods** (all use `_af_new` and would not preserve subclass type):
- Instance methods: `mul_inv` (1238), `__mul__` (1303), `__pow__` (1344), `__xor__` (1439), `__invert__` (1522), `next_lex` (1632), `commutator` (2128), `next_trotterjohnson` (2480)
- Classmethods: `unrank_nonlex` (1664), `unrank_trotterjohnson` (2426), `from_inversion_vector` (2737), `random` (2756), `unrank_lex` (2790)
- Staticmethod: `rmul_with_af` (1229)


## Craft iteration 1

**Hypothesis**: Recon diagnosis is correct - convert `_af_new` from `@staticmethod` to `@classmethod` and update all call sites.

**Actions**:
1. Changed `_af_new` signature from `@staticmethod def _af_new(perm)` to `@classmethod def _af_new(cls, perm)`
2. Updated `Basic.__new__(Perm, perm)` to `Basic.__new__(cls, perm)` in `_af_new`
3. Updated all `_af_new` call sites per recon:
   - In `__new__`: used `cls._af_new(...)`
   - In instance methods: used `self.__class__._af_new(...)`
   - In classmethods: used `self._af_new(...)`

**Gate result**: FAIL - `test_Permutation_subclassing` still failed, plus 5 other tests failed.

**Analysis**: Found additional `Perm` constructor calls and class method calls that weren't in the recon's `_af_new` call site list but still broke subclassing:
- Line 868: `return Perm(a.array_form, size=size)` in `__new__`
- Line 1242: `return Perm(other)*self` in `__rmul__`
- Line 1727: `return Perm.unrank_nonlex(...)` in `next_nonlex`
- Line 2710: `return Perm(perm)` in `josephus` classmethod

## Craft iteration 2

**Hypothesis**: The recon was correct about `_af_new`, but missed other hard-coded `Perm` references.

**Actions**:
Applied additional fixes:
1. Line 868: `Perm(a.array_form, size=size)` → `cls(a.array_form, size=size)`
2. Line 1242: `Perm(other)` → `self.__class__(other)`
3. Line 1727: `Perm.unrank_nonlex(...)` → `self.__class__.unrank_nonlex(...)`
4. Line 2710: `Perm(perm)` → `self(perm)`

**Gate result**: PASS - All 10 tests pass including `test_Permutation_subclassing`.

**Trajectory**: Divergent (progress) - the first iteration narrowed to the specific additional sites that needed fixing.

**Resolution**: RESOLVED

---

## Audit Report

### FAIL_TO_PASS
- test_Permutation_subclassing: **PASS** ✓

### PASS_TO_PASS
- test_Permutation: **ok** ✓
- test_josephus: **ok** ✓
- test_ranking: **ok** ✓
- test_mul: **ok** ✓
- test_args: **ok** ✓
- test_Cycle: **ok** ✓
- test_from_sequence: **ok** ✓
- test_printing_cyclic: **ok** ✓

### PASS_TO_PASS regressions
none

### Pre-existing (not counted)
none

### Summary
The craft patch successfully resolves the subclassing issue. All FAIL_TO_PASS tests now pass, and no PASS_TO_PASS tests regressed. The fix converted `_af_new` from a static method to a class method and updated all call sites to use `cls._af_new()` or `self.__class__._af_new()` to ensure subclass instances are returned instead of base Permutation instances.

