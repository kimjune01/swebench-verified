# Hypothesis graph: django__django-11964

## H₀: Initial diagnosis (abduction)

**Status**: Active hypothesis

**Tests fail because**: When calling `str()` on TextChoices/IntegerChoices enum members, the inherited `enum.Enum.__str__()` method returns the enum representation (e.g., "YearInSchool.FRESHMAN") instead of the string representation of the value (e.g., "FR").

**Evidence**:
- Test failure: `str(YearInSchool.FRESHMAN)` returns "YearInSchool.FRESHMAN" but test expects "FR"
- Test failure: `str(Suit.HEART)` returns "Suit.HEART" but test expects "3"
- Source: `django/db/models/enums.py` - `Choices` class inherits from `enum.Enum` but doesn't override `__str__()`
- Python's `enum.Enum.__str__()` returns `"%s.%s" % (self.__class__.__name__, self._name_)`

**Confidence**: Deduction - 95%

Traced the code path directly:
1. `TextChoices` and `IntegerChoices` inherit from `Choices`
2. `Choices` inherits from `enum.Enum`
3. No `__str__` override exists in any of these classes
4. Therefore, `enum.Enum.__str__()` is used, which returns the enum representation

**Proposed fix**: Override `__str__()` in the `Choices` class to return `str(self.value)`


## Craft gate loop

### Iteration 1

**Drafted fix**: Added `__str__` method to `Choices` class returning `str(self.value)`, removed trailing `pass`.

**codex review**: Fix is functionally correct. Noted that the override changes string representation from enum format (e.g., "YearInSchool.FRESHMAN") to value format (e.g., "FR"), which is the desired behavior. Suggested removing dead `pass` statement (applied).

**Gate result**: ✅ PASS

All 17 tests passed, including both FAIL_TO_PASS tests:
- test_str (model_enums.tests.ChoicesTests)
- test_textchoices (model_enums.tests.ChoicesTests)

**Resolution**: RESOLVED in 1 iteration. The root cause diagnosis was accurate — overriding `__str__()` in the `Choices` base class to return `str(self.value)` makes all enum members (TextChoices, IntegerChoices, etc.) stringify to their values instead of their enum representations.


## Audit

**Patch status**: Live in tree (django/db/models/enums.py: +3 -1)

### FAIL_TO_PASS
- test_str (model_enums.tests.ChoicesTests): ✅ PASS
- test_textchoices (model_enums.tests.ChoicesTests): ✅ PASS

### PASS_TO_PASS
All 15 PASS_TO_PASS tests remain passing:
- test_integerchoices: ✅ PASS
- test_integerchoices_auto_label: ✅ PASS
- test_integerchoices_containment: ✅ PASS
- test_integerchoices_empty_label: ✅ PASS
- test_integerchoices_functional_api: ✅ PASS
- test_invalid_definition: ✅ PASS
- test_textchoices_auto_label: ✅ PASS
- test_textchoices_blank_value: ✅ PASS
- test_textchoices_containment: ✅ PASS
- test_textchoices_empty_label: ✅ PASS
- test_textchoices_functional_api: ✅ PASS
- test_bool_unsupported (CustomChoicesTests): ✅ PASS
- test_labels_valid (CustomChoicesTests): ✅ PASS
- test_timezone_unsupported (CustomChoicesTests): ✅ PASS
- test_uuid_unsupported (CustomChoicesTests): ✅ PASS

### Regressions
None

### Pre-existing failures
None (all tests pass)

**Full gate output**: Ran 17 tests in 0.002s — OK

