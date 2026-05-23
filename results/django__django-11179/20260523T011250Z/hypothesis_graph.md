# Hypothesis graph: django__django-11179

## H₀: Fast delete path returns without clearing PK (abduction)

**Evidence:**
- Test `test_fast_delete_instance_set_pk_none` fails with `AssertionError: 1 is not None`
- After `u.delete()` on a User instance, `u.pk` is still `1` instead of `None`
- Test confirms User can be fast-deleted: `collector.can_fast_delete(u)` returns True

**Root cause:**
The fast delete optimization in `Collector.delete()` (django/db/models/deletion.py:275-280) returns immediately after executing the SQL delete without setting the instance's PK to None. The normal deletion path (lines 324-326) correctly sets PKs to None after deletion, but the fast delete path bypasses this.

**Code path:**
1. `Model.delete()` (base.py:910-919) creates a Collector and calls `collector.delete()`
2. `Collector.delete()` checks if fast delete is possible (line 275-277)
3. Fast delete path executes SQL delete (line 279) and returns immediately (line 280)
4. Normal path sets PK to None (line 326) but fast delete path never reaches this

**Edit site:**
- `django/db/models/deletion.py` line 280: Before the return statement, need to set `instance.pk = None`

**Confidence:** Deduction — 98%
The code path is clear and the fix location is unambiguous. The normal path explicitly sets PK to None at line 326, and the fast delete path simply needs the same behavior before its early return.


## Gate Loop — Iteration 1

**Drafted fix**: Added `setattr(instance, model._meta.pk.attname, None)` at line 280 of `django/db/models/deletion.py`, immediately after the fast delete SQL execution and before the return statement.

**codex volley**: Confirmed no breakage. The fix matches the normal path's behavior where PK is cleared after deletion regardless of count. Custom primary key field names are handled correctly via `model._meta.pk.attname`.

**Gate result**: ✅ PASS — All 42 tests pass including `test_fast_delete_instance_set_pk_none`.

**Trajectory**: Convergent-resolved — first attempt successful.


## Audit: django__django-11179

**Patch verification:**
- Patch is live: 1 file changed, 1 insertion in `django/db/models/deletion.py`
- Applied edit: `setattr(instance, model._meta.pk.attname, None)` at line 280

**Gate results (42 tests):**

### FAIL_TO_PASS
- `test_fast_delete_instance_set_pk_none (delete.tests.FastDeleteTests)`: ✅ **PASS** (was FAIL on base with `AssertionError: 1 is not None`)

### PASS_TO_PASS regressions
- **None** — All 41 PASS_TO_PASS tests remain passing

### Pre-existing failures (not counted)
- **None** — The only baseline failure was the FAIL_TO_PASS test, now resolved

**Full contract satisfied:**
- ✅ All FAIL_TO_PASS tests pass (1/1)
- ✅ Zero PASS_TO_PASS regressions (0 of 41 regressed)
- ✅ No new failures introduced

**Patch effect:** The fix correctly sets the instance PK to None after fast delete, matching the behavior of the normal deletion path. The single-line addition has no side effects on any other test.

VERDICT: RESOLVED
RE-ENTER: none
