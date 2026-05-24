# Hypothesis graph: django__django-13012

## H₀ (abduction): ExpressionWrapper returns itself instead of delegating to wrapped expression

**Symptom**: Tests fail because `ExpressionWrapper.get_group_by_cols()` returns `[self]` instead of delegating to the wrapped expression.

**Evidence**:
- Test `test_empty_group_by`: `ExpressionWrapper(Value(3)).get_group_by_cols()` returns `[ExpressionWrapper(Value(3))]` but should return `[]`
- Test `test_non_empty_group_by`: `ExpressionWrapper(Lower(Value('f'))).get_group_by_cols()` returns `[ExpressionWrapper(...)]` but should return `[Lower(Value('f'))]`

**Root cause**: 
- `ExpressionWrapper` (django/db/models/expressions.py:850) doesn't override `get_group_by_cols()`
- It inherits the default implementation from `BaseExpression` (line 350)
- Default implementation returns `[self]` when `not self.contains_aggregate`
- This is incorrect for ExpressionWrapper, which should delegate to its wrapped expression

**Supporting code**:
- `Value.get_group_by_cols()` (line 706) returns `[]` — constants don't need GROUP BY
- `ExpressionWrapper.as_sql()` (line 867) already delegates to `self.expression.as_sql()` — same pattern needed

**Confidence**: Deduction — 99%


## Craft gate-loop iteration 1

**Fix applied**: Added `get_group_by_cols()` method to `ExpressionWrapper` class at line 869-870 that delegates to the wrapped expression: `return self.expression.get_group_by_cols(alias=alias)`

**Codex pre-gate review**: Behavioral fix correct. Suggested keyword forwarding (`alias=alias`) instead of positional for clarity. No structural issues.

**Gate result**: ✓ GREEN — All 141 tests passed (2 skipped)
- `test_empty_group_by (expressions.tests.ExpressionWrapperTests)` ... ok
- `test_non_empty_group_by (expressions.tests.ExpressionWrapperTests)` ... ok

**Resolution**: FAIL_TO_PASS tests now pass. Fix is minimal (3 lines), follows existing delegation pattern in `as_sql()`, and introduces no regressions.


## Audit: django__django-13012

### Patch verification
```
django/db/models/expressions.py | 3 +++
1 file changed, 3 insertions(+)
```
Patch is live in the tree.

### FAIL_TO_PASS results
- test_empty_group_by (expressions.tests.ExpressionWrapperTests): **PASS** ✓
- test_non_empty_group_by (expressions.tests.ExpressionWrapperTests): **PASS** ✓

### PASS_TO_PASS regressions
**None.** All 141 tests passed (2 skipped).

### Pre-existing failures (confirmed against base capture)
**None.** Both FAIL_TO_PASS tests were confirmed failing on base, now passing on patched.

### Final gate output
```
Ran 141 tests in 0.165s
OK (skipped=2)
```

**VERDICT: RESOLVED**
**RE-ENTER: none**
