# Hypothesis graph: django__django-12050

## H₀ (abduction → deduction)
**Claim**: The test fails because `resolve_lookup_value` unconditionally converts list values to tuples.

**Mode**: Started as abduction from the error message, confirmed by deduction through code trace.

**Evidence**:
- Test failure: Expected `"['a', 'b']"` but got `"('a', 'b')"`
- `django/db/models/sql/query.py:1076`: `value = tuple(resolved_values)`
- This line always converts the result to tuple regardless of input type

**Call path**:
1. `test_iterable_lookup_value` → `query.build_where(Q(name=['a', 'b']))`
2. `build_where` → `_add_q` → `build_filter` (line 1206)
3. `build_filter` (line 1258) → `resolve_lookup_value(['a', 'b'], ...)`
4. `resolve_lookup_value` (line 1076) → returns `('a', 'b')`
5. `Exact.__init__` (line 23) → `get_prep_lookup()` (line 73) → `CharField.get_prep_value`
6. `CharField.to_python` (line 1015) → `str(('a', 'b'))` → `"('a', 'b')"`

**Root cause**: Line 1076 in `django/db/models/sql/query.py` introduced in commit 8a281aa7fe (fixing #30687) always converts to tuple.

**Confidence**: 95% (deduction - traced through code, identified exact line)

**Status**: Active hypothesis

## Gate loop iteration 1

**Fix applied**: Changed line 1076 in `django/db/models/sql/query.py` from:
```python
value = tuple(resolved_values)
```
to:
```python
value = type(value)(resolved_values)
```

**Rationale**: Preserve the original iterable type (list or tuple) by using the type constructor instead of hard-coding tuple conversion.

**Gate result**: ✅ PASS - All 11 tests passed, including `test_iterable_lookup_value`

**Trajectory**: Convergent-resolved - The minimal fix directly addressed the root cause with no regressions.

---

## Audit: django__django-12050

### Patch confirmation
```
django/db/models/sql/query.py | 2 +-
1 file changed, 1 insertion(+), 1 deletion(-)
```

### FAIL_TO_PASS
- test_iterable_lookup_value: **PASS** ✓

### PASS_TO_PASS results
All 10 tests remain passing:
- test_clone_select_related: PASS
- test_complex_query: PASS
- test_foreign_key: PASS
- test_foreign_key_exclusive: PASS
- test_foreign_key_f: PASS
- test_multiple_fields: PASS
- test_negated_nullable: PASS
- test_simple_query: PASS
- test_simplecol_query: PASS
- test_transform: PASS

### PASS_TO_PASS regressions
None

### Pre-existing failures (not counted)
None

### Summary
All FAIL_TO_PASS tests now pass, and zero PASS_TO_PASS regressions detected. The fix successfully preserves the original iterable type by using `type(value)(resolved_values)` instead of unconditionally converting to tuple.
