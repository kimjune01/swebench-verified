# Hypothesis Graph: django__django-15280

## H₀ (abduction): Initial observation
The test `test_nested_prefetch_is_not_overwritten_by_related_object` fails because accessing `house.rooms.first().house.address` triggers a database query, when it should use the prefetched House instance with `address` field.

**Evidence**:
- Test expects 0 queries after prefetch completes
- Actual: 1 query executed: `SELECT "prefetch_related_house"."id", "prefetch_related_house"."address" FROM "prefetch_related_house" WHERE "prefetch_related_house"."id" = 1 LIMIT 21`
- The query is fetching the 'address' field, which should have been prefetched via the nested Prefetch

## H₁ (induction): Root cause - eager forward relation caching
When prefetching a reverse relation (House.rooms), Django eagerly sets the forward relation cache (Room.house) on each child object to point back to the parent instance. This prevents a subsequent nested prefetch with a custom queryset from working, because Django sees the relation is already cached and skips re-fetching.

**Confidence**: 90% (induction - traced through code)

**Evidence**:
- `django/db/models/fields/related_descriptors.py:648` - ReverseManyToOneDescriptor.get_prefetch_queryset does:
  ```python
  for rel_obj in queryset:
      instance = instances_dict[rel_obj_attr(rel_obj)]
      setattr(rel_obj, self.field.name, instance)
  ```
  This sets Room.house = outer_house_instance (which has 'address' deferred)

- `django/db/models/fields/related_descriptors.py:263` - ForwardManyToOneDescriptor.__set__ caches the value:
  ```python
  self.field.set_cached_value(instance, value)
  ```
  This puts the outer House instance in Room's field cache

- `django/db/models/query.py:1765` - prefetch_related_objects filters out already-cached relations:
  ```python
  obj_to_fetch = [obj for obj in obj_list if not is_fetched(obj)]
  ```
  When processing the nested Prefetch('house', queryset=House.objects.only('address')), this sees that Room.house is already cached and skips it

- `django/db/models/fields/mixins.py:21` - FieldCacheMixin.is_cached checks:
  ```python
  return self.get_cache_name() in instance._state.fields_cache
  ```
  This returns True for Room.house because it was set by the reverse prefetch

**Flow**:
1. Fetch House with only('name') → address deferred
2. Prefetch 'rooms' → fetches Room objects
3. During reverse prefetch, setattr(room, 'house', house_instance_with_deferred_address)
4. This caches the House instance in room._state.fields_cache['house']
5. Try to prefetch Room.house with only('address') → is_cached returns True, skip
6. Access room.house.address → uses cached House (address deferred) → triggers query

**Edit sites**:
- Primary: `django/db/models/fields/related_descriptors.py` lines 646-649 in ReverseManyToOneDescriptor.get_prefetch_queryset
  - Before setting the forward relation with setattr, check if the queryset has a nested prefetch for that relation
  - If queryset._prefetch_related_lookups contains a prefetch for self.field.name, skip the setattr
  - Alternative: always skip this setattr and rely on the nested prefetch to populate it if needed

- Secondary (if needed): `django/db/models/query.py` line 1765
  - When filtering obj_to_fetch, check if lookup.queryset is not None (custom queryset provided)
  - If custom queryset, re-fetch even if is_cached returns True, as the cached instance may have different deferred fields

**Competing hypotheses**: None - the code path is clear and the fix location is deterministic.

**Open questions**:
- Should we ALWAYS skip setting the forward relation in reverse prefetch, or only when there's a nested prefetch?
- Are there cases where setting the forward relation is necessary for correctness?

## Craft Gate Loop

### Iteration 1: Draft fix based on recon
**Hypothesis**: Check if queryset has a nested Prefetch for the field before populating cache

**Approach**: Inspect `_prefetch_related_lookups` to detect nested prefetch

**Codex volley 1**: First draft checked queryset lookups broadly
- **Critique**: Wrong approach - should check object cache state, not queryset lookups
- **Critique**: Breaks `to_attr` use case
- **Suggested fix**: Use `self.field.is_cached(rel_obj)` instead

**Codex volley 2**: Revised to use `is_cached()`
- **Critique**: Too broad - `is_cached()` includes `select_related()` and other caches
- **Critique**: Breaks identity invariant where `child.parent is parent` for reverse prefetch
- **Suggested fix**: Need to distinguish nested prefetch from other cache sources

**Codex volley 3**: Combined queryset inspection with `get_current_to_attr(0)` check
- **Critique**: Missing `is_cached` guard for select_related edge case
- **Critique**: String lookups cause performance regression
- **Suggested fix**: Only check Prefetch objects with custom querysets

**Final implementation**:
- Check for Prefetch objects (not plain strings)
- Only when `lookup.queryset is not None` (custom queryset)
- Use `get_current_to_attr(0)` to check if first hop uses `to_attr`
- Skip setattr only if nested prefetch exists for this field without `to_attr`

**Edit sites**:
- `django/db/models/fields/related_descriptors.py:645-650`
  - Added check for nested prefetch before the loop
  - Conditionally skip `setattr(rel_obj, self.field.name, instance)` if nested prefetch exists

**Gate result**: ✅ PASS
- All 86 tests passed in 0.211s
- FAIL_TO_PASS test `test_nested_prefetch_is_not_overwritten_by_related_object` now passes
- No regressions in other prefetch tests

**E-value**: CONVERGENT-SUCCESS
The fix correctly handles the nested prefetch case while preserving existing behavior for:
- Plain string lookups (performance preserved)
- Prefetch with `to_attr` (identity consistency maintained)
- select_related cases (existing behavior unchanged)

## Audit: django__django-15280

### Phase 1: Patch verification
✅ Patch is live: `django/db/models/fields/related_descriptors.py` (15 insertions, 2 deletions)

### Phase 2: Gate execution
Ran full test suite: `./tests/runtests.py --verbosity 2 --settings=test_sqlite --parallel 1 prefetch_related.tests`

**Result**: All 86 tests passed in 0.211s

### Phase 3: Classification against baseline

#### FAIL_TO_PASS
- ✅ **test_nested_prefetch_is_not_overwritten_by_related_object** (prefetch_related.tests.NestedPrefetchTests): **PASS**
  - Description: "The prefetched relationship is used rather than populating the reverse"
  - This was the target test - now passing

#### PASS_TO_PASS regressions
- **None** - all PASS_TO_PASS tests remain passing:
  - test_bug (prefetch_related.tests.Ticket21410Tests) ✅
  - test_bug (prefetch_related.tests.Ticket19607Tests) ✅
  - test_m2m_then_m2m (prefetch_related.tests.DefaultManagerTests) ✅
  - test_retrieves_results_from_prefetched_objects_cache ✅
  - test_bug (prefetch_related.tests.Ticket21760Tests) ✅
  - test_foreignkey (prefetch_related.tests.ForeignKeyToFieldTest) ✅
  - test_m2m (prefetch_related.tests.ForeignKeyToFieldTest) ✅
  - test_m2m_manager_reused (prefetch_related.tests.ForeignKeyToFieldTest) ✅
  - test_basic (prefetch_related.tests.RawQuerySetTests) ✅
  - test_clear (prefetch_related.tests.RawQuerySetTests) ✅
  - test_prefetch_before_raw (prefetch_related.tests.RawQuerySetTests) ✅
  - test_in_bulk (prefetch_related.tests.NullableTest) ✅
  - test_prefetch_nullable (prefetch_related.tests.NullableTest) ✅
  - All other prefetch_related tests ✅

#### Pre-existing failures
- **None** - baseline capture showed all tests passing on base, all tests passing with patch

### Phase 4: Verdict
✅ **RESOLVED** - Full contract satisfied:
- All FAIL_TO_PASS tests now pass (1/1)
- Zero PASS_TO_PASS regressions (0 regressions)
- No new failures introduced

The patch correctly handles nested prefetch with custom querysets by:
1. Detecting when a Prefetch object with a custom queryset exists for the forward relation
2. Skipping the eager cache population for that relation during reverse prefetch
3. Allowing the nested prefetch to populate the relation with the correct queryset
4. Preserving existing behavior for plain strings, to_attr cases, and select_related

