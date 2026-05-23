# Hypothesis graph: django__django-13315

## Hypothesis H1: Missing DISTINCT in limit_choices_to queryset (DEDUCTION, 95%)

**Node type:** Root cause hypothesis
**Reasoning mode:** Deduction
**Confidence:** 95%

### Observation
Test `test_limit_choices_to_no_duplicates` fails with:
- `threepwood` appears 4 times instead of 1
- `marley` appears 3 times instead of 1

When ForeignKey uses `limit_choices_to` with multiple related lookups (joins), the queryset contains duplicates.

### Root Cause
File: `django/forms/models.py`, line 103

```python
def apply_limit_choices_to_to_formfield(formfield):
    """Apply limit_choices_to to the formfield's queryset if needed."""
    if hasattr(formfield, 'queryset') and hasattr(formfield, 'get_limit_choices_to'):
        limit_choices_to = formfield.get_limit_choices_to()
        if limit_choices_to is not None:
            formfield.queryset = formfield.queryset.complex_filter(limit_choices_to)
```

The `complex_filter()` method applies the filter but doesn't deduplicate results. When `limit_choices_to` contains multiple related lookups (e.g., `jokes__funny=True, jokes_today__funny=True`), the SQL JOIN creates a cartesian product:

For `threepwood`:
- `jokes` relation: joke1, joke2 (2 funny jokes via ForeignKey)
- `jokes_today` relation: joke1, joke3 (2 funny jokes via M2M)
- Cartesian product: 2 × 2 = 4 duplicate rows

For `marley`:
- `jokes` relation: joke3 (1 funny joke via ForeignKey)
- `jokes_today` relation: joke1, joke2, joke3 (3 funny jokes via M2M)
- Cartesian product: 1 × 3 = 3 duplicate rows

### Solution
Add `.distinct()` after `complex_filter()` to deduplicate:

```python
formfield.queryset = formfield.queryset.complex_filter(limit_choices_to).distinct()
```

### Evidence Trail
1. Error shows exact duplicate counts: 4 for threepwood, 3 for marley
2. Traced from test → ModelForm → apply_limit_choices_to_to_formfield → complex_filter
3. complex_filter (django/db/models/query.py:968) just applies filter via add_q, no deduplication
4. Multiple related lookups create JOIN combinations that multiply rows
5. distinct() is safe: idempotent, minimal cost for form choice querysets

### Edit Sites
- `django/forms/models.py` line 103: Add `.distinct()` after `complex_filter(limit_choices_to)`


## Craft gate-loop node 1

**Iteration:** 1
**Action:** Applied `.distinct()` to `formfield.queryset.complex_filter(limit_choices_to)` at `django/forms/models.py:103`
**codex pre-review:** Raised concerns about ordering edge cases, performance impact on all formfields, and PostgreSQL `DISTINCT ON` compatibility. Suggested `Exists` subquery approach.
**Gate result:** ✅ PASS - `test_limit_choices_to_no_duplicates` passes
**Trajectory:** Convergent - direct resolution in 1 iteration

The minimal fix (adding `.distinct()`) successfully deduplicates the queryset results caused by cartesian products from multiple related lookups. codex's theoretical concerns did not manifest in practice for this test case.


## Audit: django__django-13315

**Timestamp:** 2026-05-22
**Gate result:** All 149 tests passed

### FAIL_TO_PASS
- `test_limit_choices_to_no_duplicates (model_forms.tests.LimitChoicesToTests)`: **PASS** ✓

### PASS_TO_PASS regressions
None — all 149 tests in the suite passed.

### Pre-existing failures (not counted)
None identified in the baseline or current run.

### Patch summary
```diff
diff --git a/django/forms/models.py b/django/forms/models.py
index 5d115458a1..f993bb9c98 100644
--- a/django/forms/models.py
+++ b/django/forms/models.py
@@ -100,7 +100,7 @@def apply_limit_choices_to_to_formfield(formfield):
     if hasattr(formfield, 'queryset') and hasattr(formfield, 'get_limit_choices_to'):
         limit_choices_to = formfield.get_limit_choices_to()
         if limit_choices_to is not None:
-            formfield.queryset = formfield.queryset.complex_filter(limit_choices_to)
+            formfield.queryset = formfield.queryset.complex_filter(limit_choices_to).distinct()
```

The fix adds `.distinct()` to deduplicate queryset results when `limit_choices_to` contains multiple related lookups that create cartesian products via JOINs. Minimal, targeted, no regressions.

