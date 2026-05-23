# Hypothesis graph: django__django-16256

## H₀ (Initial observation - abduction)
**Status**: CONFIRMED as root cause  
**Mode**: Deduction (95%)  
**Created**: Phase 1 baseline

The tests fail because async methods `acreate()`, `aget_or_create()`, and `aupdate_or_create()` called on related managers (both many-to-many and reverse foreign key) are inherited from QuerySet and do not establish the relationship between objects.

**Evidence**:
- Test `test_acreate` creates object via `await self.mtm1.simples.acreate(field=2)` but `await self.mtm1.simples.acount()` returns 0 instead of 1
- Test `test_acreate_reverse` creates object via `await self.s1.relatedmodel_set.acreate()` but count is 0 instead of 1
- Error trace shows: `SimpleModel.DoesNotExist: SimpleModel matching query does not exist` when trying to retrieve the supposedly created object from the related manager

## H₁ (Root cause localization - deduction)
**Status**: ACTIVE  
**Mode**: Deduction (95%)  
**Confidence basis**: Direct code inspection and stack trace analysis

**Suspect set**:
- `django/db/models/fields/related_descriptors.py` lines 630-850: `create_reverse_many_to_one_manager` function
- `django/db/models/fields/related_descriptors.py` lines 941-1220: `create_forward_many_to_many_manager` function

**Root cause explanation**:
The async methods are NOT defined in RelatedManager classes. When called, they are inherited from QuerySet base class. The QuerySet async methods (e.g., `acreate` at query.py:678) do:
```python
async def acreate(self, **kwargs):
    return await sync_to_async(self.create)(**kwargs)
```

At runtime, `self.create` resolves to `QuerySet.create` instead of `RelatedManager.create` because the async method lives in QuerySet. This bypasses the relationship-establishing logic:

**For reverse many-to-one** (related_descriptors.py:793-797):
```python
def create(self, **kwargs):
    self._check_fk_val()
    kwargs[self.field.name] = self.instance  # <-- SKIPPED
    db = router.db_for_write(self.model, instance=self.instance)
    return super(RelatedManager, self.db_manager(db)).create(**kwargs)
```

**For many-to-many** (related_descriptors.py:1185-1190):
```python
def create(self, *, through_defaults=None, **kwargs):
    db = router.db_for_write(self.instance.__class__, instance=self.instance)
    new_obj = super(ManyRelatedManager, self.db_manager(db)).create(**kwargs)
    self.add(new_obj, through_defaults=through_defaults)  # <-- SKIPPED
    return new_obj
```

## H₂ (Fix specification - deduction)
**Status**: READY FOR IMPLEMENTATION  
**Mode**: Deduction (98%)

**Required changes**:

1. **Import sync_to_async** (line ~66 in related_descriptors.py):
   - Add: `from asgiref.sync import sync_to_async`
   - Pattern matches query.py:10

2. **Add async methods to reverse many-to-one manager** (after line 793, 800, 807):
   - Add `acreate()` wrapping `self.create` with `sync_to_async`
   - Add `aget_or_create()` wrapping `self.get_or_create` with `sync_to_async`
   - Add `aupdate_or_create()` wrapping `self.update_or_create` with `sync_to_async`
   - Each should have `.alters_data = True` attribute

3. **Add async methods to many-to-many manager** (after lines 1191, 1204, 1217):
   - Add `acreate()` wrapping `self.create` with `sync_to_async`
   - Add `aget_or_create()` wrapping `self.get_or_create` with `sync_to_async`
   - Add `aupdate_or_create()` wrapping `self.update_or_create` with `sync_to_async`
   - Each should have `.alters_data = True` attribute

**Why this works**:
By defining the async methods directly in RelatedManager, `self.create` will resolve to `RelatedManager.create` (not `QuerySet.create`), preserving the relationship-establishing logic. The pattern matches the problem statement's suggested fix.

## Rejected hypotheses
None - the root cause is clear from code inspection and matches the problem statement exactly.

## Open questions
None - implementation is straightforward.
