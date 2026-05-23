# Hypothesis Graph: django__django-16901

## H₀ (Abduction): Initial observation
The test `test_filter_multiple` fails because it expects [1, 2, 5, 6, 9] but gets [1, 2]. Missing numbers 5, 6, 9 all satisfy 3 or 5 conditions (odd count > 1).

**Evidence**: Test output shows:
```
AssertionError: Element counts were not equal:
First has 0, Second has 1:  <Number: 5>
First has 0, Second has 1:  <Number: 6>
First has 0, Second has 1:  <Number: 9>
```

## H₁ (Deduction): Root cause identified
**File**: `django/db/models/sql/where.py:133-144`
**Issue**: XOR fallback for databases without native XOR support uses wrong logic

Current code (line 142):
```python
rhs = Exact(1, rhs_sum)
```

This checks if sum == 1 (exactly one condition true), but XOR semantics require **parity** checking (odd number of conditions true).

**Mathematical proof**:
- XOR is associative: (a XOR b) XOR c = a XOR (b XOR c)
- Binary XOR: a XOR b = a + b (mod 2)
- n-ary XOR: a XOR b XOR c = (a + b + c) mod 2
- Result is true when odd number of operands are true

**Expected behavior for test case**:
```
Q(num__gte=1) ^ Q(num__gte=3) ^ Q(num__gte=5) ^ Q(num__gte=7) ^ Q(num__gte=9)

num=0: 0+0+0+0+0 = 0 (even) → False ✓
num=1: 1+0+0+0+0 = 1 (odd)  → True  ✓
num=2: 1+0+0+0+0 = 1 (odd)  → True  ✓
num=3: 1+1+0+0+0 = 2 (even) → False ✓
num=4: 1+1+0+0+0 = 2 (even) → False ✓
num=5: 1+1+1+0+0 = 3 (odd)  → True  ✓
num=6: 1+1+1+0+0 = 3 (odd)  → True  ✓
num=7: 1+1+1+1+0 = 4 (even) → False ✓
num=8: 1+1+1+1+0 = 4 (even) → False ✓
num=9: 1+1+1+1+1 = 5 (odd)  → True  ✓
```

Current code matches only sum==1 (nums 1,2).
Correct code should match sum%2==1 (nums 1,2,5,6,9).

**Confidence**: Deduction — 99% (traced through code, verified mathematical semantics)

## Edit sites

### Primary fix: `django/db/models/sql/where.py`

**Line 1**: Add import (after line 8):
```python
from django.db.models.functions import Mod
```

**Lines 142**: Change from:
```python
rhs = Exact(1, rhs_sum)
```
to:
```python
rhs = Exact(1, Mod(rhs_sum, 2))
```

**Comment update (lines 136-138)**: The comment should be updated to reflect correct semantics:
From: `(a OR b OR c OR ...) AND (a + b + c + ...) == 1`
To: `(a OR b OR c OR ...) AND (a + b + c + ...) % 2 == 1`

## Historical context

Introduced in commit c6b4d62fa2 (Fixed #29865 -- Added logical XOR support for Q() and querysets).
Original implementation had incorrect interpretation of n-ary XOR semantics.

## Gate Loop Node 1 (RESOLVED)

**Iteration**: 1  
**Status**: ✅ RESOLVED  
**Evidence**: All 7 XOR tests pass, including `test_filter_multiple`

**Fix applied**:
- Added import: `from django.db.models.functions import Mod`
- Updated XOR fallback comment to reflect parity semantics: `(a + b + c + ...) % 2 == 1`
- Conditionally wrap `rhs_sum` with `Mod(rhs_sum, 2)` only when `len(self.children) > 2`
  - Binary XOR (`a XOR b`) remains unchanged (already correct with `sum == 1`)
  - N-ary XOR (3+ operands) now checks odd parity instead of exactly-one

**Codex feedback incorporated**:
- Avoided changing SQL for binary XOR (common case)
- Only applies `Mod()` for 3+ operands where parity matters

**Gate output**: All tests OK (7/7 passed)

**Trajectory**: Convergent-success (first iteration)

---

# Audit: django__django-16901

## FAIL_TO_PASS
- `test_filter_multiple`: **PASS** ✓

## PASS_TO_PASS regressions
None

## Pre-existing failures (not counted)
None

## Verification
All 7 tests in `xor_lookups.tests.XorLookupsTests` pass:
- test_empty_in: ok
- test_exclude: ok
- test_filter: ok
- test_filter_multiple: ok ← **FIXED** (was FAIL on base)
- test_filter_negated: ok
- test_pk_q: ok
- test_stages: ok

The patch correctly implements n-ary XOR parity semantics by wrapping `rhs_sum` with `Mod(rhs_sum, 2)` for cases with 3+ operands, while preserving the existing binary XOR behavior.

VERDICT: RESOLVED
RE-ENTER: none
