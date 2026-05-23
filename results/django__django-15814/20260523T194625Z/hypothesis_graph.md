# Hypothesis graph: django__django-15814

## Hypothesis H₀ (Recon Round 1)

**Date**: 2026-05-23
**Type**: Abduction → Deduction (95%)

**Symptom**:
```
ValueError: 'baseuser_ptr_id' is not in list
```
at `/testbed/django/db/models/query.py:2599`

**Model hierarchy**:
- `BaseUser` (concrete, has `name` field, auto pk `id`)
- `TrackerUser(BaseUser)` (concrete, adds `status`, has auto parent link `baseuser_ptr_id` as pk)
- `ProxyTrackerUser(TrackerUser)` (proxy)
- `Issue` has ForeignKey to `ProxyTrackerUser`

**Query**: `Issue.objects.select_related("assignee").only("assignee__status")`

**Root Cause**:
When `deferred_to_data()` processes `only("assignee__status")` with a ForeignKey to a proxy model:

1. Line 751: `opts = cur_model._meta` where `cur_model = ProxyTrackerUser`
2. Line 757: Stores pk under `must_include[ProxyTrackerUser]`
3. Line 759-767: For "status" field, computes `model = field.model._meta.concrete_model = TrackerUser`
4. Line 763-764: Since `model (TrackerUser) != opts.model (ProxyTrackerUser)`, stores under `seen[TrackerUser]`
5. Result: `only_load[ProxyTrackerUser] = {'baseuser_ptr_id'}`, `only_load[TrackerUser] = {'status'}`
6. In `get_default_columns()` line 840: checks `field.model in only_load`
7. For `baseuser_ptr` field: `field.model = TrackerUser`, which IS in `only_load`, but `'baseuser_ptr_id'` NOT in `only_load[TrackerUser]` → field skipped
8. Pk missing from columns → missing from `init_list` → `ValueError` in `RelatedPopulator.__init__`

**Fix**:
Change line 751 in `/testbed/django/db/models/sql/query.py`:
```python
# From:
opts = cur_model._meta

# To:
opts = cur_model._meta.concrete_model._meta
```

This ensures that when `opts.model` is compared with `field.model._meta.concrete_model` at line 763, they match for fields on the concrete model, causing `model = cur_model` (the proxy), storing both pk and field under the same key `ProxyTrackerUser`. Then in `get_default_columns`, since `field.model (TrackerUser)` is not in `only_load` (which only has `ProxyTrackerUser`), fields are not filtered incorrectly.

**Evidence**:
- `django/db/models/sql/query.py:751` - where opts is assigned from proxy model's _meta
- `django/db/models/sql/query.py:757` - where pk is stored with cur_model as key
- `django/db/models/sql/query.py:763-764` - where model key is determined by comparing with opts.model
- `django/db/models/sql/compiler.py:840` - where field.model is checked against only_load keys

**Confidence**: Deduction, 95% (traced through code logic, matches problem statement's suggested fix)


---

## Gate iteration 1 — RESOLVED

**Applied fix**: Changed line 762 in `/testbed/django/db/models/sql/query.py`:
```python
# Before:
if model == opts.model:
# After:
if model == opts.concrete_model:
```

**Rationale**: Normalize the comparison to use concrete models on both sides. When `opts.model` is a proxy (e.g., `ProxyTrackerUser`), and `model` is already the concrete model (e.g., `TrackerUser`), the comparison now succeeds (`TrackerUser == TrackerUser`), triggering `model = cur_model` to store fields under the proxy model key in the `only_load` dict.

This fix preserves `opts = cur_model._meta` (keeping proxy metadata for field resolution) while only normalizing the ownership comparison, avoiding the "too broad" issue codex flagged with the original approach of changing line 751 to `opts = cur_model._meta.concrete_model._meta`.

**Gate result**: ✅ All 30 tests passed
- `test_select_related_only` now passes
- No PASS_TO_PASS regressions

**Codex review**: Approved after volley. "Functionally, this fix looks right for the stated bug. It preserves `opts` as the proxy model's `_meta`, but normalizes only the ownership comparison."

---

# Audit: django__django-15814

## FAIL_TO_PASS
- test_select_related_only (proxy_models.tests.ProxyModelTests): **PASS** ✓

## PASS_TO_PASS regressions
None - all 29 PASS_TO_PASS tests continue to pass.

## Pre-existing (not counted, confirmed against base capture)
None

## Patch summary
The fix changes line 762 in `django/db/models/sql/query.py`:
```diff
-            if model == opts.model:
+            if model == opts.concrete_model:
```

This ensures that when resolving select_related fields, Django compares against the concrete model rather than potentially comparing a concrete model against a proxy model, which was causing the KeyError when using select_related with only() on proxy models.

All 30 tests pass, including the target FAIL_TO_PASS test with zero regressions.

VERDICT: RESOLVED
RE-ENTER: none
