# Hypothesis graph: django__django-16256

## H1: Async methods not overridden in related managers (INITIAL)

**Type**: Abduction  
**Confidence**: 85%

**Hypothesis**: Related managers (RelatedManager, ManyRelatedManager, GenericRelatedObjectManager) override sync methods `create()`, `get_or_create()`, and `update_or_create()` to automatically set relationship fields. However, the async versions (`acreate`, `aget_or_create`, `aupdate_or_create`) are only defined in QuerySet and are not overridden in related managers. When called on a related manager, these async methods are inherited from QuerySet but don't properly invoke the related manager's overridden sync methods, causing relationship fields to not be set.

**Evidence**:
- `django/db/models/fields/related_descriptors.py:788-810`: RelatedManager overrides create/get_or_create/update_or_create to set `kwargs[self.field.name] = self.instance`
- `django/db/models/fields/related_descriptors.py:1186-1220`: ManyRelatedManager overrides create/get_or_create/update_or_create to call `self.add(obj)` after creation
- `django/contrib/contenttypes/fields.py:741-766`: GenericRelatedObjectManager overrides create/get_or_create/update_or_create to set content_type and object_id fields
- No async versions found in any related manager: `grep -n "async def acreate" related_descriptors.py` returns nothing
- Test failures show objects created but not added to relations (count=0) or IntegrityError for missing relationship fields

**Edit sites**:
1. `django/db/models/fields/related_descriptors.py` line ~65: Add `from asgiref.sync import sync_to_async` to imports
2. `django/db/models/fields/related_descriptors.py` after line 794 (after `create.alters_data = True` in RelatedManager): Add `acreate` method
3. `django/db/models/fields/related_descriptors.py` after line 802 (after `get_or_create.alters_data = True` in RelatedManager): Add `aget_or_create` method
4. `django/db/models/fields/related_descriptors.py` after line 810 (after `update_or_create.alters_data = True` in RelatedManager): Add `aupdate_or_create` method
5. `django/db/models/fields/related_descriptors.py` after line 1193 (after `create.alters_data = True` in ManyRelatedManager): Add `acreate` method
6. `django/db/models/fields/related_descriptors.py` after line 1206 (after `get_or_create.alters_data = True` in ManyRelatedManager): Add `aget_or_create` method
7. `django/db/models/fields/related_descriptors.py` after line 1220 (after `update_or_create.alters_data = True` in ManyRelatedManager): Add `aupdate_or_create` method
8. `django/contrib/contenttypes/fields.py` line ~1: Add `from asgiref.sync import sync_to_async` to imports
9. `django/contrib/contenttypes/fields.py` after line 749 (after `create.alters_data = True` in GenericRelatedObjectManager): Add `acreate` method
10. `django/contrib/contenttypes/fields.py` after line 757 (after `get_or_create.alters_data = True` in GenericRelatedObjectManager): Add `aget_or_create` method
11. `django/contrib/contenttypes/fields.py` after line 766 (after `update_or_create.alters_data = True` in GenericRelatedObjectManager): Add `aupdate_or_create` method

Each async method should be implemented as:
```python
async def acreate(self, **kwargs):
    return await sync_to_async(self.create)(**kwargs)

acreate.alters_data = True
```

And similarly for aget_or_create and aupdate_or_create, matching the signature of their sync counterparts (including through_defaults parameter for M2M methods).


## Gate Loop 1

**Action**: Applied fix to add async wrappers in related managers that call sync methods via `sync_to_async`.

**Changes**:
- `django/db/models/fields/related_descriptors.py`: Added `from asgiref.sync import sync_to_async` import
- `django/db/models/fields/related_descriptors.py`: Added `acreate()`, `aget_or_create()`, `aupdate_or_create()` async methods to RelatedManager (reverse FK)
- `django/db/models/fields/related_descriptors.py`: Added `acreate()`, `aget_or_create()`, `aupdate_or_create()` async methods to ManyRelatedManager (M2M), preserving `through_defaults` parameter
- `django/contrib/contenttypes/fields.py`: Added `from asgiref.sync import sync_to_async` import
- `django/contrib/contenttypes/fields.py`: Added `acreate()`, `aget_or_create()`, `aupdate_or_create()` async methods to GenericRelatedObjectManager

**Gate Output**: PASS - All 64 tests passed, including all 9 FAIL_TO_PASS tests:
- test_acreate (async.test_async_related_managers.AsyncRelatedManagersOperationTest) ... ok
- test_acreate_reverse (async.test_async_related_managers.AsyncRelatedManagersOperationTest) ... ok
- test_aget_or_create (async.test_async_related_managers.AsyncRelatedManagersOperationTest) ... ok
- test_aget_or_create_reverse (async.test_async_related_managers.AsyncRelatedManagersOperationTest) ... ok
- test_aupdate_or_create (async.test_async_related_managers.AsyncRelatedManagersOperationTest) ... ok
- test_aupdate_or_create_reverse (async.test_async_related_managers.AsyncRelatedManagersOperationTest) ... ok
- test_generic_async_acreate (generic_relations.tests.GenericRelationsTests) ... ok
- test_generic_async_aget_or_create (generic_relations.tests.GenericRelationsTests) ... ok
- test_generic_async_aupdate_or_create (generic_relations.tests.GenericRelationsTests) ... ok

**E-value**: Convergent-resolved — first iteration, green gate.

**Codex volley**: Codex confirmed the fix shape was correct, flagged missing imports and signature requirements — all addressed before gate run.

---

## Audit: django__django-16256

**Patch Status**: Live (47 insertions across 2 files)

**Gate Result**: **PASS** - All 64 tests passed

### FAIL_TO_PASS Results
- ✓ test_acreate (async.test_async_related_managers.AsyncRelatedManagersOperationTest) — PASS
- ✓ test_acreate_reverse (async.test_async_related_managers.AsyncRelatedManagersOperationTest) — PASS
- ✓ test_aget_or_create (async.test_async_related_managers.AsyncRelatedManagersOperationTest) — PASS
- ✓ test_aget_or_create_reverse (async.test_async_related_managers.AsyncRelatedManagersOperationTest) — PASS
- ✓ test_aupdate_or_create (async.test_async_related_managers.AsyncRelatedManagersOperationTest) — PASS
- ✓ test_aupdate_or_create_reverse (async.test_async_related_managers.AsyncRelatedManagersOperationTest) — PASS
- ✓ test_generic_async_acreate (generic_relations.tests.GenericRelationsTests) — PASS
- ✓ test_generic_async_aget_or_create (generic_relations.tests.GenericRelationsTests) — PASS
- ✓ test_generic_async_aupdate_or_create (generic_relations.tests.GenericRelationsTests) — PASS

**Total FAIL_TO_PASS**: 9/9 passing

### PASS_TO_PASS Regressions
None — all 55 PASS_TO_PASS tests remain passing.

### Pre-existing Failures
None — the fail-on-base capture showed IntegrityError failures that are now resolved by the patch.

### Summary
The patch successfully resolves all failing tests by adding async method wrappers (`acreate`, `aget_or_create`, `aupdate_or_create`) to three related manager classes:
- RelatedManager (reverse FK)
- ManyRelatedManager (M2M)
- GenericRelatedObjectManager (generic relations)

Each async method delegates to its sync counterpart via `sync_to_async`, ensuring relationship fields are properly set during object creation. Zero regressions introduced.

VERDICT: RESOLVED
RE-ENTER: none
