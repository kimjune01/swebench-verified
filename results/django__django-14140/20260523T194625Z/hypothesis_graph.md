# Hypothesis graph: django__django-14140
# Hypothesis Graph: django__django-14140

## H₀: Initial abduction
**Claim**: The tests fail because Q.deconstruct() assumes single non-Q children are always tuples and tries to subscript them.

**Evidence**:
- Error: `TypeError: 'Exists' object is not subscriptable` at django/db/models/query_utils.py:90
- Line 90: `kwargs = {child[0]: child[1]}` assumes child is subscriptable
- Tests expect `Q(Exists(...))` to deconstruct to `args=(Exists(...),)` not `kwargs`

**Mode**: Abduction (pattern matching from error trace)
**Status**: Active hypothesis
**Confidence**: 90%

## Root Cause Analysis

The Q.deconstruct() method at lines 88-90 contains a special case added in 2016 (commit 508b5deb):
```python
if len(self.children) == 1 and not isinstance(self.children[0], Q):
    child = self.children[0]
    kwargs = {child[0]: child[1]}  # Line 90 - assumes 2-tuple
```

This special case was designed to reverse the transformation in `__init__`:
- `Q(field=value)` → `children=[('field', value)]` → deconstruct back to `kwargs={'field': value}`

However, it breaks when a single child is NOT a tuple:
- `Q(Exists(...))` → `children=[Exists(...)]` → tries `Exists(...)[0]` → TypeError

The fix: Remove the special case so all single children go to args, matching the new test expectations.

## Suspect Files
- `django/db/models/query_utils.py` lines 88-90: The problematic subscripting code


## craft iteration 1 (RESOLVED)

**Drafted fix**: Removed the special case in `Q.deconstruct()` at lines 88-90 that assumed single children are subscriptable tuples. Changed to always use `args = tuple(self.children)` for all cases.

**codex review**: Confirmed the fix addresses the crashes and failing tests. Noted the behavior change is intentional - all single-child Q objects now deconstruct to args instead of kwargs. Suggested additional test coverage but acknowledged the fix is correct.

**Applied patch**:
```diff
--- a/django/db/models/query_utils.py
+++ b/django/db/models/query_utils.py
@@ -85,11 +85,9 @@ class Q(tree.Node):
         if path.startswith('django.db.models.query_utils'):
             path = path.replace('django.db.models.query_utils', 'django.db.models')
         args, kwargs = (), {}
-        if len(self.children) == 1 and not isinstance(self.children[0], Q):
-            child = self.children[0]
-            kwargs = {child[0]: child[1]}
-        else:
-            args = tuple(self.children)
-            if self.connector != self.default:
-                kwargs = {'_connector': self.connector}
+        args = tuple(self.children)
+        if self.connector != self.default:
+            kwargs = {'_connector': self.connector}
         if self.negated:
             kwargs['_negated'] = True
         return path, args, kwargs
```

**Gate result**: PASS - All FAIL_TO_PASS tests passed (207 tests, 0 failures, 2 skipped).

**Evidence trajectory**: Convergent → RESOLVED. The fix directly addressed the root cause - removing the subscripting assumption for single children.

---

# Audit: django__django-14140

## FAIL_TO_PASS
- test_deconstruct (queries.test_q.QTests): **PASS**
- test_deconstruct_boolean_expression (queries.test_q.QTests): **PASS**
- test_deconstruct_negated (queries.test_q.QTests): **PASS**
- test_boolean_expression_combined_with_empty_Q (expressions.tests.BasicExpressionsTests): **PASS**

## PASS_TO_PASS regressions
None. All 207 tests passed (2 skipped).

## Pre-existing (not counted, confirmed against base capture)
None. The base capture showed all PASS_TO_PASS tests passing on the unpatched repo, and they all still pass with the patch.

## Kill report
Not applicable - patch RESOLVED the issue.

The patch successfully removed the problematic subscripting assumption in `Q.deconstruct()` at lines 88-90. All four FAIL_TO_PASS tests now pass, and the full test suite (207 tests across expressions.tests, queries.test_q, and queryset_pickle.tests) runs clean with zero regressions.

VERDICT: RESOLVED
RE-ENTER: none
