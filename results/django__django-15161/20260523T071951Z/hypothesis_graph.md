# Hypothesis graph: django__django-15161

## Hypothesis H₀ (Abduction)
**Time**: 2026-05-22
**Mode**: Abduction
**Confidence**: 95%

### Observation
The failing tests expect simplified deconstruct paths for expression classes:
- `test_deconstruct` expects `Value().deconstruct()` to return `'django.db.models.Value'` but gets `'django.db.models.expressions.Value'`
- `test_deconstruct_output_field` has the same issue with Value
- `test_serialize_complex_func_index` expects serialized expressions to use simplified paths like `models.Func`, `models.Case`, `models.When`, `models.Value`, `models.ExpressionWrapper`, `models.OrderBy`

### Root cause
The F() class was updated in PR #14047 to use `@deconstructible(path='django.db.models.F')` decorator, which makes it deconstruct to the simplified path. However, other expression classes (Value, Func, Case, When, ExpressionWrapper, OrderBy) do not have this decorator and still deconstruct to their full module path `django.db.models.expressions.*`.

### Evidence
1. `django/db/models/expressions.py:527` - F class has decorator:
   ```python
   @deconstructible(path='django.db.models.F')
   class F(Combinable):
   ```

2. All other classes lack the decorator:
   - `django/db/models/expressions.py:654` - `class Func(SQLiteNumericMixin, Expression):`
   - `django/db/models/expressions.py:734` - `class Value(SQLiteNumericMixin, Expression):`
   - `django/db/models/expressions.py:956` - `class ExpressionWrapper(SQLiteNumericMixin, Expression):`
   - `django/db/models/expressions.py:988` - `class When(Expression):`
   - `django/db/models/expressions.py:1055` - `class Case(SQLiteNumericMixin, Expression):`
   - `django/db/models/expressions.py:1228` - `class OrderBy(Expression):`

3. All these classes are exported from `django.db.models.__init__.py` so they can be accessed as `models.ClassName`

4. The `deconstructible` decorator from `django.utils.deconstruct` allows specifying a custom import path via the `path` parameter

### Hypothesis
Adding `@deconstructible(path='django.db.models.<ClassName>')` decorator to each of the six expression classes (Func, Value, Case, When, ExpressionWrapper, OrderBy) will make them deconstruct to the simplified path, passing all three failing tests.


---

## Craft Gate Loop

### Iteration 1: Initial Fix

**Action**: Added `@deconstructible(path='django.db.models.X')` decorators to 6 expression classes:
- Func (line 653)
- Value (line 734)
- ExpressionWrapper (line 956)
- When (line 988)
- Case (line 1055)
- OrderBy (line 1228)

**Codex Review**: Approved. Confirmed that:
1. Decorator placement matches the F class pattern
2. The `deconstructible` implementation already has `type(obj) is klass` guard to protect subclass deconstruction
3. All 6 classes are properly exported from `django.db.models.__init__`

**Gate Result**: ✅ PASS

All FAIL_TO_PASS tests passed:
- test_deconstruct (expressions.tests.ValueTests) ... ok
- test_deconstruct_output_field (expressions.tests.ValueTests) ... ok
- test_serialize_complex_func_index (migrations.test_writer.WriterTests) ... ok

Total: Ran 214 tests in 0.180s - OK (skipped=1, expected failures=1)

**Status**: RESOLVED

---

## Audit: django__django-15161

**Timestamp**: 2026-05-22
**Patch status**: Live (django/db/models/expressions.py modified, 6 insertions, 8 deletions)

### FAIL_TO_PASS Results
- `test_deconstruct (expressions.tests.ValueTests)`: **PASS** ✓
- `test_deconstruct_output_field (expressions.tests.ValueTests)`: **PASS** ✓
- `test_serialize_complex_func_index (migrations.test_writer.WriterTests)`: **PASS** ✓

### PASS_TO_PASS Regressions
None. All 214 tests passed (skipped=1, expected failures=1).

### Pre-existing Failures (not counted)
None detected. The fail-on-base capture showed `test_serialize_complex_func_index` was failing on base, and it now passes.

### Verdict Summary
The craft patch successfully resolves all three FAIL_TO_PASS tests with zero regressions. The decorator approach correctly aligns the deconstruct paths for all six expression classes (Func, Value, Case, When, ExpressionWrapper, OrderBy) with the pattern established by the F class.

VERDICT: RESOLVED
RE-ENTER: none
