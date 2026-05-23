# Hypothesis Graph: django__django-13590

## H₀ (Abduction): Initial symptom
The test `test_range_lookup_namedtuple` fails with `TypeError: __new__() missing 1 required positional argument: 'maximum'` when filtering with a namedtuple argument to `__range`.

## H₁ (Deduction): Root cause identified
**Location**: `django/db/models/sql/query.py:1077-1083` in `resolve_lookup_value` method

**Diagnosis**: The method reconstructs tuples/lists after resolving inner expressions using:
```python
return type(value)(
    self.resolve_lookup_value(sub_value, can_reuse, allow_joins)
    for sub_value in value
)
```

This passes a generator expression as a single argument to the type constructor. Regular `tuple()` and `list()` accept an iterable as their single argument, so this works fine. However, namedtuples require positional arguments for each field (e.g., `EmployeeRange(minimum, maximum)`), not an iterable.

**Evidence**:
- Stack trace shows error at line 1082 in `resolve_lookup_value`
- Commit 8be79984 (2019-11-10) introduced this pattern to preserve list vs tuple types (fixing #30971)
- Namedtuples have `isinstance(nt, tuple) == True` so they match the condition
- Namedtuples have a `_fields` attribute distinguishing them from regular tuples

**Confidence**: Deduction - 98% (traced through code, verified behavior)

## Fix specification
**Edit site**: `django/db/models/sql/query.py` lines 1077-1083

**Change needed**: 
Detect namedtuples (via `_fields` attribute) and unpack the generator with `*` for those, while passing the generator as-is for regular tuples/lists:

```python
resolved = (
    self.resolve_lookup_value(sub_value, can_reuse, allow_joins)
    for sub_value in value
)
value_type = type(value)
# Namedtuples need unpacking, regular tuple/list accept an iterable
if hasattr(value_type, '_fields'):
    return value_type(*resolved)
else:
    return value_type(resolved)
```

This preserves the existing behavior for lists and regular tuples while fixing namedtuples.

## craft gate iteration 1

**Status:** RESOLVED ✓

**Change applied:**
Modified `django/db/models/sql/query.py:1077-1086` in the `resolve_lookup_value` method to detect namedtuples and unpack them correctly.

**Fix logic:**
1. Store the generator expression in a variable `resolved`
2. Get the value type as `value_type`
3. Check if it's a tuple with `_fields` attribute (namedtuple marker)
4. If namedtuple: unpack with `*` → `value_type(*resolved)`
5. Otherwise: pass generator as single arg → `value_type(resolved)`

**codex pre-gate review:**
- Tightened condition from `hasattr(value_type, '_fields')` to `isinstance(value, tuple) and hasattr(value, '_fields')` to avoid catching custom list subclasses with `_fields` attribute
- Confirmed the approach is sound for regular tuples, lists, and namedtuples

**Gate result:**
```
Ran 149 tests in 0.181s
OK (skipped=2)
```

All FAIL_TO_PASS tests now pass:
- ✓ `test_range_lookup_namedtuple (expressions.tests.IterableLookupInnerExpressionsTests)`

No regressions detected.

---

## Audit: django__django-13590

**Patch confirmed live:** `django/db/models/sql/query.py` modified (7 insertions, 1 deletion)

### Phase 2: Gate execution
```
Ran 149 tests in 0.184s
OK (skipped=2)
```

### Phase 3: Classification

**FAIL_TO_PASS:**
- ✓ `test_range_lookup_namedtuple (expressions.tests.IterableLookupInnerExpressionsTests)` — **PASS**

**PASS_TO_PASS status:**
All PASS_TO_PASS tests verified passing in gate output:
- ✓ test_empty_group_by (expressions.tests.ExpressionWrapperTests)
- ✓ test_non_empty_group_by (expressions.tests.ExpressionWrapperTests)
- ✓ test_deconstruct (expressions.tests.FTests)
- ✓ test_deepcopy (expressions.tests.FTests)
- ✓ test_equal (expressions.tests.FTests)
- ✓ test_hash (expressions.tests.FTests)
- ✓ test_not_equal_Value (expressions.tests.FTests)
- ✓ test_optimizations (expressions.tests.ExistsTests)
- ✓ test_and (expressions.tests.CombinableTests)
- ✓ test_negation (expressions.tests.CombinableTests)
- ✓ test_or (expressions.tests.CombinableTests)
- ✓ test_reversed_and (expressions.tests.CombinableTests)
- ✓ test_reversed_or (expressions.tests.CombinableTests)
- ✓ test_aggregates (expressions.tests.ReprTests)
- ✓ test_distinct_aggregates (expressions.tests.ReprTests)
- ✓ test_expressions (expressions.tests.ReprTests)

**Regressions:** None

**Pre-existing failures:** None (all 149 tests passed)

### Phase 4: Verdict
All FAIL_TO_PASS tests now pass ✓
Zero PASS_TO_PASS regressions ✓
Contract satisfied.
