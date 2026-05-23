# Hypothesis graph: django__django-11603

## H₀ (Abduction, ~85%)
**The tests fail because the `Avg` and `Sum` aggregate classes do not have `allow_distinct = True` set.**

### Evidence:
- `/testbed/django/db/models/aggregates.py:26` - The base `Aggregate.__init__` raises `TypeError("%s does not allow distinct." % self.__class__.__name__)` when `distinct=True` is passed but `self.allow_distinct` is `False`
- `/testbed/django/db/models/aggregates.py:21` - The base `Aggregate` class sets `allow_distinct = False` by default
- `/testbed/django/db/models/aggregates.py:106` - The `Count` class explicitly sets `allow_distinct = True`, which is why it works
- `/testbed/django/db/models/aggregates.py:99` - The `Avg` class does NOT set `allow_distinct = True`
- `/testbed/django/db/models/aggregates.py:147` - The `Sum` class does NOT set `allow_distinct = True`

### Test Failure:
```
ERROR: test_distinct_on_aggregate (aggregation.tests.AggregateTestCase) (aggregate='Avg')
TypeError: Avg does not allow distinct.

ERROR: test_distinct_on_aggregate (aggregation.tests.AggregateTestCase) (aggregate='Sum')
TypeError: Sum does not allow distinct.
```

### Root Cause:
The infrastructure for DISTINCT support was added in commit bc05547cd8 (Fixed #28658), which added:
1. The `allow_distinct` attribute to the base `Aggregate` class (defaults to `False`)
2. Validation in `__init__` that raises `TypeError` if `distinct=True` is passed but `allow_distinct=False`
3. Updated `Count` to set `allow_distinct = True`

However, `Avg` and `Sum` were not updated to set `allow_distinct = True`, so they inherited the default `False` value and now throw an exception when `distinct=True` is passed.

### Edit Sites:
1. `/testbed/django/db/models/aggregates.py` lines 99-101 (Avg class): Add `allow_distinct = True`
2. `/testbed/django/db/models/aggregates.py` lines 147-149 (Sum class): Add `allow_distinct = True`

### Confidence: Deduction - 95%
This is a straightforward code trace:
- Test calls `Avg('rating', distinct=True)`
- `Avg.__init__` calls `Aggregate.__init__(*expressions, distinct=True, **extra)`
- `Aggregate.__init__` checks `if distinct and not self.allow_distinct` → True (because `allow_distinct=False` by default)
- Raises `TypeError("Avg does not allow distinct.")`

The fix is to add `allow_distinct = True` to both classes, following the same pattern as `Count`.

---

## /craft gate loop — iteration 1

**Patch applied:**
```diff
--- a/django/db/models/aggregates.py
+++ b/django/db/models/aggregates.py
@@ -99,6 +99,7 @@ class Aggregate(Func):
 class Avg(FixDurationInputMixin, NumericOutputFieldMixin, Aggregate):
     function = 'AVG'
     name = 'Avg'
+    allow_distinct = True
 
 
 class Count(Aggregate):
@@ -147,6 +148,7 @@ class StdDev(NumericOutputFieldMixin, Aggregate):
 class Sum(FixDurationInputMixin, Aggregate):
     function = 'SUM'
     name = 'Sum'
+    allow_distinct = True
 
 
 class Variance(NumericOutputFieldMixin, Aggregate):
```

**codex pre-gate review:** "No blocking issue in the proposed diff. Verdict: patch is minimal and correct for the stated failures."

**Gate result:** ✓ PASS — all 60 tests passed, including both FAIL_TO_PASS tests:
- `test_distinct_on_aggregate (aggregation.tests.AggregateTestCase) ... ok`
- `test_empty_aggregate (aggregation.tests.AggregateTestCase) ... ok`

**Trajectory:** Convergent (first attempt) — recon diagnosis was correct, minimal fix applied, green gate on iteration 1.

---

## /audit — final verification

**Patch verified live in tree:**
```
 django/db/models/aggregates.py | 2 ++
 1 file changed, 2 insertions(+)
```

**Full gate execution:** All 60 tests passed (0.081s)

### FAIL_TO_PASS results:
- test_distinct_on_aggregate (aggregation.tests.AggregateTestCase): **PASS** ✓
- test_empty_aggregate (aggregation.tests.AggregateTestCase): **PASS** ✓

### PASS_TO_PASS regressions:
None. All 60 tests passed.

### Pre-existing failures (not counted):
None.

**Fix summary:** Adding `allow_distinct = True` to `Avg` and `Sum` aggregate classes resolved both FAIL_TO_PASS tests with no regressions. The patch correctly mirrors the pattern already established by the `Count` aggregate class.

VERDICT: RESOLVED
RE-ENTER: none
