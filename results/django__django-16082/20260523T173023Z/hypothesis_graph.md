# Hypothesis graph: django__django-16082

## H₀: Missing MOD operator in mixed-type numeric combinations (ACTIVE)

**Mode**: Deduction  
**Confidence**: 99%

### Observation
Running `/tmp/gate-django_django-16082` produces 4 test errors, all from `test_resolve_output_field_number` with the MOD operator (`%%`):
- IntegerField MOD DecimalField
- DecimalField MOD IntegerField  
- IntegerField MOD FloatField
- FloatField MOD IntegerField

Each raises: `FieldError: Cannot infer type of '%%' expression involving these types: IntegerField, DecimalField. You must set output_field.`

Error originates from `django/db/models/expressions.py:659` in `CombinedExpression._resolve_output_field()`.

### Trace
1. Test creates `CombinedExpression(IntegerField, Combinable.MOD, DecimalField)`
2. Accessing `expr.output_field` triggers `_resolve_output_field()` (line 653)
3. Calls `_resolve_combined_type(connector='%%', lhs_type=IntegerField, rhs_type=DecimalField)` (line 622)
4. Function looks up connector in `_connector_combinators` dict, iterates through registered combinations
5. No match found, returns None
6. Line 658 checks if `combined_type is None`, raises FieldError at line 659

### Root cause
`_connector_combinations` list (lines 504-598) has three blocks for numeric operations:

**Block 1 (lines 506-522)**: Same-type operands  
Connectors: ADD, SUB, MUL, DIV, **MOD**, POW ✓

**Block 2 (lines 523-536)**: Different-type operands  
Connectors: ADD, SUB, MUL, DIV (MOD missing ✗)

**Block 3 (lines 546-564)**: NULL handling  
Connectors: ADD, SUB, MUL, DIV, **MOD**, POW ✓

MOD is present in blocks 1 and 3 but absent from block 2, so mixed-type MOD operations fail to resolve.

### Fix specification
**File**: `django/db/models/expressions.py`  
**Location**: Line 535  
**Change**: Add `Combinable.MOD,` to the connector tuple after `Combinable.DIV,`

Current code (lines 532-536):
```python
        for connector in (
            Combinable.ADD,
            Combinable.SUB,
            Combinable.MUL,
            Combinable.DIV,
        )
```

Should become:
```python
        for connector in (
            Combinable.ADD,
            Combinable.SUB,
            Combinable.MUL,
            Combinable.DIV,
            Combinable.MOD,
        )
```

This registers the same type resolution rules for MOD as for the other arithmetic operators:
- IntegerField MOD DecimalField → DecimalField
- DecimalField MOD IntegerField → DecimalField
- IntegerField MOD FloatField → FloatField
- FloatField MOD IntegerField → FloatField

### Evidence
- `django/db/models/expressions.py:519` — Block 1 includes MOD
- `django/db/models/expressions.py:532-535` — Block 2 excludes MOD
- `django/db/models/expressions.py:562` — Block 3 includes MOD
- `tests/expressions/tests.py:2424` — Test expects MOD to behave like ADD, SUB, MUL, DIV

## Craft gate loop

### Iteration 1: Initial fix

**Diagnosis**: MOD operator missing from the second `_connector_combinations` block (mixed numeric types).

**Applied diff**:
```diff
--- a/django/db/models/expressions.py
+++ b/django/db/models/expressions.py
@@ -532,6 +532,7 @@
             Combinable.SUB,
             Combinable.MUL,
             Combinable.DIV,
+            Combinable.MOD,
         )
     },
```

**codex pre-gate review**: "No blocking issue in the proposed diff. Adding `Combinable.MOD` to the mixed numeric combinations is the right narrow fix."

**Gate result**: ✅ PASS — All 175 tests passed, including both FAIL_TO_PASS tests:
- `test_resolve_output_field_number (expressions.tests.CombinedExpressionTests)` 
- `test_resolve_output_field_with_null (expressions.tests.CombinedExpressionTests)`

**Resolution**: RESOLVED in 1 iteration.

---

# Audit: django__django-16082

## Patch Summary
```diff
django/db/models/expressions.py | 1 +
 1 file changed, 1 insertion(+)
 
Added Combinable.MOD to _connector_combinations to resolve output field for modulo operations.
```

## FAIL_TO_PASS Results
- `test_resolve_output_field_number`: **PASS** ✓
- `test_resolve_output_field_with_null`: **PASS** ✓

Both target tests now pass. The fix correctly adds MOD to the connector combinations, allowing output field resolution for modulo expressions.

## PASS_TO_PASS Regressions
**None**

All PASS_TO_PASS tests remain passing. The one-line addition to `_connector_combinations` is surgical and introduces no side effects.

## Pre-existing Failures (not counted)
- `test_mixed_comparisons1 (expressions.tests.FTimeDeltaTests)`: expected failure (pre-existing, confirmed in base capture)

## Gate Summary
- Ran 175 tests in 0.166s
- OK (skipped=1, expected failures=1)
- 2/2 FAIL_TO_PASS now passing
- 0 regressions
- Clean gate

VERDICT: RESOLVED
RE-ENTER: none
