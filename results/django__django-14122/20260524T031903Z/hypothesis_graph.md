# Hypothesis graph: django__django-14122

## H₀: Initial Observation (abduction)
The test `test_default_ordering_does_not_affect_group_by` fails because Django includes Meta.ordering fields in the GROUP BY clause when it shouldn't. The query `Article.objects.values('author').annotate(count=Count('author'))` should group by `author_id` only, but the generated SQL groups by `author_id, pub_date, headline, author__name, second_author__name` (all fields from Meta.ordering), causing incorrect aggregation.

**Evidence:**
- Test expects 2 groups: `{'author': 1, 'count': 3}` and `{'author': 2, 'count': 1}`
- Test gets 3+ groups with `count=1` each
- Generated SQL: `GROUP BY "ordering_article"."author_id", "ordering_article"."pub_date", "ordering_article"."headline", "ordering_author"."name", T3."name"`

## H₁: Root Cause (deduction - 95%)

**Root cause:** In `django/db/models/sql/compiler.py`, the `get_group_by()` method (lines 128-132) unconditionally adds ORDER BY expressions to the GROUP BY clause, including those from Meta.ordering. Commit 0ddb4ebf fixed half the problem by removing Meta.ordering from the final ORDER BY clause (line 600), but failed to prevent those same fields from being added to GROUP BY earlier in the process.

**Code path:**
1. `pre_sql_setup()` (line 56) calls `get_order_by()` which includes Meta.ordering fields and sets `self._meta_ordering` (line 288)
2. `pre_sql_setup()` (line 61) calls `get_group_by(select, order_by)` passing the order_by that includes Meta.ordering
3. Inside `get_group_by()` lines 128-132, the code adds ALL non-reference order_by expressions to GROUP BY without checking if they're from Meta.ordering:
   ```python
   for expr, (sql, params, is_ref) in order_by:
       if not is_ref:
           expressions.extend(expr.get_group_by_cols())
   ```
4. Later in `as_sql()` (line 600), the ORDER BY is removed if `self._meta_ordering` is set, but the damage to GROUP BY is already done

**Supporting evidence:**
- `django/db/models/sql/compiler.py:128-132` - unconditional addition of order_by to GROUP BY
- `django/db/models/sql/compiler.py:288` - `self._meta_ordering` flag is set when Meta.ordering is used
- `django/db/models/sql/compiler.py:600` - ORDER BY is cleared for Meta.ordering, but GROUP BY was already built
- Commit 0ddb4ebf only fixed ORDER BY removal, not GROUP BY pollution

**Confidence:** Deduction - 95% (traced the code path, reproduced the exact SQL, verified the flag exists)

## Edit Sites

**Primary fix:**
- `django/db/models/sql/compiler.py` lines 128-132: Skip adding order_by expressions to GROUP BY when `self._meta_ordering` is set

The fix should check `self._meta_ordering` before the loop that adds order_by to GROUP BY:
```python
# Skip ORDER BY expressions from Meta.ordering - they shouldn't affect GROUP BY
if not (hasattr(self, '_meta_ordering') and self._meta_ordering):
    for expr, (sql, params, is_ref) in order_by:
        # Skip References to the select clause, as all expressions in the
        # select clause are already part of the group by.
        if not is_ref:
            expressions.extend(expr.get_group_by_cols())
```

**No other edit sites identified** - the flag `self._meta_ordering` is already set correctly, and the ORDER BY removal is already in place. Only the GROUP BY logic needs the fix.

## Craft gate loop

### Iteration 1: Draft and apply fix

**Diagnosis applied:** Recon identified that `get_group_by()` at lines 128-132 unconditionally adds ORDER BY expressions to GROUP BY, even when they come from Meta.ordering. The `_meta_ordering` flag is set but not checked.

**Fix:** Wrapped the order_by loop with condition `if not getattr(self, '_meta_ordering', None):` to skip adding Meta.ordering fields to GROUP BY.

**codex pre-gate review:** 
- Confirmed the fix addresses the root cause
- Suggested using `getattr` instead of `hasattr() and` for cleaner style
- Verified that `_meta_ordering` is only set when ALL ordering comes from Meta.ordering (explicit `.order_by()` takes a different branch)
- No concerns about breaking explicit ordering or mixed ordering scenarios

**Gate result:** ✅ PASS
- `test_default_ordering_does_not_affect_group_by` now passes
- All 27 ordering tests pass
- No regressions

**Changed files:**
- `django/db/models/sql/compiler.py` (lines 128-133): Added conditional to skip order_by→GROUP BY when `_meta_ordering` is set

**Resolution:** RESOLVED — FAIL_TO_PASS test passes, no regressions

## Audit: django__django-14122

### FAIL_TO_PASS
- `test_default_ordering_does_not_affect_group_by`: ✅ PASS (was FAIL on base)

### PASS_TO_PASS regressions
None - all 27 tests pass

### Pre-existing failures (not counted)
None

### Verification
- Patch applied: 6 insertions, 5 deletions in `django/db/models/sql/compiler.py`
- Gate run: All 27 tests in ordering.tests.OrderingTests pass
- Contract satisfied: FAIL_TO_PASS now passes, zero regressions

The fix correctly prevents Meta.ordering fields from polluting the GROUP BY clause by checking `_meta_ordering` before adding order_by expressions to the GROUP BY list. The test now produces the expected 2 groups instead of 3+.

