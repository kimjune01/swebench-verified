# Hypothesis graph: django__django-13406

## H₁ [abduction → 85%]: Query setter doesn't restore _iterable_class

**Symptom:** After unpickling a query with values()/values_list(), the reloaded queryset returns model instances instead of dictionaries.

**Evidence:**
- Test failures show: `AssertionError: <Happening object> != {'name': 'test', ...}`
- `django/db/models/query.py:831`: `values()` sets `clone._iterable_class = ValuesIterable`
- `django/db/models/query.py:858-861`: `values_list()` sets `_iterable_class` to ValuesListIterable/FlatValuesListIterable/NamedValuesListIterable
- `django/db/models/query.py:211-213`: query setter just assigns `self._query = value` without updating `_iterable_class`
- `django/db/models/sql/query.py:207`: Query has `values_select` attribute that stores field names from values()/values_list()
- `django/db/models/sql/query.py:2224`: `set_values()` sets `self.values_select = tuple(field_names)`

**Root cause:**
The QuerySet's `query.setter` doesn't check if the assigned Query has `values_select` set. When a query is created via `values()` or `values_list()`, the Query object stores the field list in `values_select`, but the QuerySet's `_iterable_class` is what determines the return type (dict vs model instance). During normal operation, `values()` creates a clone and sets both `query.set_values()` AND `_iterable_class = ValuesIterable`. But when unpickling:
1. User pickles `qs.query` (only the Query object, not the QuerySet's `_iterable_class`)
2. User creates fresh QuerySet: `reloaded = Model.objects.all()` → `_iterable_class = ModelIterable`
3. User assigns unpickled query: `reloaded.query = unpickled_query`
4. The setter assigns the query but doesn't update `_iterable_class` based on `query.values_select`
5. Result: Query knows it should return dictionaries (`values_select` is set), but QuerySet uses ModelIterable

**Competing considerations:**
- `values_list()` uses ValuesListIterable (returns tuples), but we can't distinguish between `values()` and `values_list()` from the Query alone
- Test comment says: "values_list() is reloaded to values() when using a pickled query"
- This indicates the intended behavior is to degrade `values_list()` to `values()` (dict) after unpickling

**Fix:**
`django/db/models/query.py` lines 211-213: In `query.setter`, check if `value.values_select` is non-empty, and if so, set `self._iterable_class = ValuesIterable`.

```python
@query.setter
def query(self, value):
    self._query = value
    if value.values_select:
        self._iterable_class = ValuesIterable
```

**Confidence:** 85% (abduction)
- The trace is clear: query setter doesn't update _iterable_class
- The Query has all needed information (values_select)
- The fix is simple and localized
- Uncertainty: might there be other state to restore? (edge cases with annotations, extra, etc.)


---

## Gate Loop (Craft Phase)

### Iteration 1: Initial Implementation

**Hypothesis**: The recon diagnosis is correct - the query setter needs to check `values_select` and restore `_iterable_class = ValuesIterable`.

**Initial draft**: Simple check for `values_select`:
```python
@query.setter
def query(self, value):
    self._query = value
    if value.values_select:
        self._iterable_class = ValuesIterable
```

**Codex review**: Flagged that `values_select` is too narrow - it only catches values queries with model fields. For annotation-only queries like `.annotate(x=Max('y')).values('x')`, `values_select` is empty `()` but `annotation_select_mask` is set to `{'x'}`. The setter must check all three indicators of values mode.

**Revised implementation**:
```python
@query.setter
def query(self, value):
    self._query = value
    if (value.values_select or
        value.annotation_select_mask is not None or
        value.extra_select_mask is not None):
        self._iterable_class = ValuesIterable
```

**Codex second review**: Approved. Handles field-only, annotation-only, mixed, and extra() values queries. Leaves plain `annotate()` alone (masks are None). Cannot restore specific ValuesListIterable variants, but that's expected per test comments.

**Gate result**: ✅ PASS
- test_annotation_values: ok
- test_annotation_values_list: ok  
- test_annotation_with_callable_default: ok
- All 35 tests in queryset_pickle: ok

**Resolution**: The fix correctly restores `ValuesIterable` for all forms of pickled values/values_list queries by checking the three Query attributes that indicate values mode: `values_select` (model fields), `annotation_select_mask` (selected annotations), and `extra_select_mask` (selected extra columns).

---

## Audit: django__django-13406

**Patch verified live:**
```
django/db/models/query.py | 4 ++++
1 file changed, 4 insertions(+)
```

### FAIL_TO_PASS (all 3 must pass)
- test_annotation_values: ✅ PASS
- test_annotation_values_list: ✅ PASS
- test_annotation_with_callable_default: ✅ PASS

### PASS_TO_PASS regressions
None. All 32 PASS_TO_PASS tests continue to pass.

### Pre-existing failures (not counted, confirmed against base capture)
None.

### Gate result
```
Ran 35 tests in 0.035s

OK
```

All tests passed. The fix successfully restores `_iterable_class = ValuesIterable` when the query setter receives a Query with values_select, annotation_select_mask, or extra_select_mask set, resolving the pickle/unpickle regression while preserving all existing behavior.

VERDICT: RESOLVED
RE-ENTER: none

