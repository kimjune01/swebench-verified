# Hypothesis graph: django__django-11815

## H0: Initial abduction (2026-05-23)

**Hypothesis**: The tests fail because `EnumSerializer` serializes enum members by their value instead of by their name, causing the output to be `EnumClass(value)` instead of `EnumClass['name']`.

**Mode**: Abduction → Deduction (traced through code)
**Confidence**: 99% (deduction)

**Evidence**:
1. Test failure output shows:
   - Expected: `migrations.test_writer.TextEnum['A']`
   - Actual: `migrations.test_writer.TextEnum('a-value')`
   - Expected: `re.RegexFlag['DOTALL']`
   - Actual: `re.RegexFlag(16)`

2. `django/db/migrations/serializer.py:119-125` - `EnumSerializer.serialize()`:
   ```python
   def serialize(self):
       enum_class = self.value.__class__
       module = enum_class.__module__
       v_string, v_imports = serializer_factory(self.value.value).serialize()
       imports = {'import %s' % module, *v_imports}
       return "%s.%s(%s)" % (module, enum_class.__name__, v_string), imports
   ```
   - Line 123: serializes `self.value.value` (the enum member's value)
   - Line 125: formats as `EnumClass(value)` using constructor-call syntax

3. Enum objects have both `.name` and `.value` attributes:
   - `TextEnum.A.name` → `'A'`
   - `TextEnum.A.value` → `'a-value'`
   - The serializer currently uses `.value` but should use `.name`

4. The bracket notation `EnumClass['name']` is valid Python for accessing enum members by name.

**Root cause**: `EnumSerializer` uses `self.value.value` and constructor syntax instead of `self.value.name` and bracket notation.

**Status**: Active hypothesis, ready for fix

## Craft gate-loop iteration 1

**Drafted diff:**
Changed `EnumSerializer.serialize()` in `django/db/migrations/serializer.py` to use bracket notation with enum member name instead of constructor syntax with value:
- Removed line serializing the enum value: `v_string, v_imports = serializer_factory(self.value.value).serialize()`
- Changed imports to: `imports = {'import %s' % module}`
- Changed return to: `return "%s.%s[%r]" % (module, enum_class.__name__, self.value.name), imports`

**codex volley:**
codex confirmed the diff is "basically correct" for the two failing tests. Noted that:
- Fix correctly changes `TextEnum('a-value')` to `TextEnum['A']`
- Fix correctly changes `re.RegexFlag(16)` to `re.RegexFlag['DOTALL']`
- Removing `v_imports` is correct since enum value is no longer serialized
- Using `%r` for the name is acceptable and matches Django's serializer style

**Gate result: PASS**
All 46 tests passed, including both FAIL_TO_PASS tests:
- test_serialize_enums
- test_serialize_class_based_validators

**Status: RESOLVED**

---

## Audit: django__django-11815

### FAIL_TO_PASS
- test_serialize_class_based_validators (migrations.test_writer.WriterTests): **PASS** ✓
- test_serialize_enums (migrations.test_writer.WriterTests): **PASS** ✓

### PASS_TO_PASS regressions
None. All 44 PASS_TO_PASS tests remain passing.

### Pre-existing failures (not counted, confirmed against base capture)
None. The two FAIL_TO_PASS tests were the only failures on base.

### Verification
Gate output: All 46 tests passed in 0.020s

The patch successfully:
1. Fixed enum serialization to use bracket notation with `.name` instead of constructor syntax with `.value`
2. Maintained all existing test behavior (zero regressions)
3. Resolved both failing tests from the baseline

VERDICT: RESOLVED
RE-ENTER: none
