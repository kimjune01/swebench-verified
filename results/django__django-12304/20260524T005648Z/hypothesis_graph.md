# Hypothesis graph: django__django-12304

## H₀: Initial hypothesis (abduction)

**Root cause:** Django template system calls enum classes when resolving attribute chains, causing enumeration types to be unusable in templates.

**Evidence:**
- Test failure: `test_templates` expects `'Diamond|1'` but gets `'|'` (empty output)
- Template: `{{ Suit.DIAMOND.label }}|{{ Suit.DIAMOND.value }}`
- Both `Suit.DIAMOND.label` and `Suit.DIAMOND.value` resolve to empty strings

**Mechanism:**
1. Template resolution in `django/template/base.py` lines 827-866
2. When resolving `Suit.DIAMOND.label`, first lookup gets the `Suit` class
3. Line 851: checks if `Suit` is callable → yes (all classes are callable)
4. Line 852: checks for `do_not_call_in_templates` attribute → not present
5. Line 857-858: tries to call `Suit()` with no arguments
6. Fails with TypeError because enum requires a value argument
7. Lines 860-864: determines arguments were required, sets current to `string_if_invalid` (empty string)
8. Subsequent lookups (`DIAMOND`, `label`) fail on empty string

**Verification:**
- Confirmed enum classes are callable: `callable(Suit)` → True
- Confirmed enum members are NOT callable: `callable(Suit.DIAMOND)` → False
- Template resolution code at `django/template/base.py:851-866` implements the call-if-callable logic
- The `do_not_call_in_templates` flag is the standard Django mechanism to prevent template auto-calling

**Confidence:** Deduction - 95%

This is traced from the code path, not an experiment. The logic is deterministic and matches the observed failure.

## Craft: Implementation

**Initial approach (REJECTED by codex):**
- Attempted to add `do_not_call_in_templates = True` inside the `Choices` class body (after docstring, before `__str__`)
- **codex catch:** Python enum treats plain class-body assignments as enum members
- This would make `do_not_call_in_templates` an enum member, preventing subclassing: `TypeError: IntegerChoices: cannot extend enumeration 'Choices'`

**Revised approach:**
- Set `cls.do_not_call_in_templates = True` in `ChoicesMeta.__new__()` after class creation
- Placement: after `cls.label = property(...)` line, before `return enum.unique(cls)`
- This sets the attribute on each created enum class without making it a member

**Implementation:**
File: `django/db/models/enums.py`
```python
class ChoicesMeta(enum.EnumMeta):
    def __new__(metacls, classname, bases, classdict):
        # ... existing code ...
        cls = super().__new__(metacls, classname, bases, classdict)
        cls._value2label_map_ = dict(zip(cls._value2member_map_, labels))
        cls.label = property(lambda self: cls._value2label_map_.get(self.value))
        cls.do_not_call_in_templates = True  # ← Added
        return enum.unique(cls)
```

**Gate iteration 1:** ✓ PASS
- All 18 tests passed, including `test_templates`
- FAIL_TO_PASS: `test_templates (model_enums.tests.ChoicesTests)` now passes
- Output: `'Diamond|1'` (expected)
- No regressions

**Status:** RESOLVED - gate green on first attempt after codex structural review

## Audit: django__django-12304

**Patch verified live:**
```
django/db/models/enums.py | 1 +
```

**Full gate results:** All 18 tests PASS (0.003s)

### FAIL_TO_PASS
- `test_templates (model_enums.tests.ChoicesTests)`: **PASS** ✓
  - Base failure: `AssertionError: '|' != 'Diamond|1'`
  - Now returns: `'Diamond|1'` (expected)

### PASS_TO_PASS regressions
**None** - all 17 PASS_TO_PASS tests remain passing

### Pre-existing failures
**None** - `test_templates` was the only failing test on base, now fixed

### Final classification
- All FAIL_TO_PASS tests now pass: ✓
- Zero regressions: ✓
- Clean resolution with minimal surgical fix (1 line)

**VERDICT:** RESOLVED  
**RE-ENTER:** none
