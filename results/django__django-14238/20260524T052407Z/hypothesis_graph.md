# Hypothesis graph: django__django-14238

## Hypothesis H₀ (Abduction, 2026-05-23)

**Node:** Initial baseline observation

**Symptom:** Two test failures:
1. `test_issubclass_of_autofield` - `issubclass(MyBigAutoField, models.AutoField)` returns False when it should return True
2. `test_default_auto_field_setting_bigautofield_subclass` - raises ValueError "Primary key 'model_options.test_default_pk.MyBigAutoField' referred by DEFAULT_AUTO_FIELD must subclass AutoField"

**Root cause:** `AutoFieldMeta.__subclasscheck__` uses identity check (`in`) instead of inheritance check, failing to recognize subclasses of BigAutoField/SmallAutoField as AutoField subclasses.

**Evidence:**
- `django/db/models/fields/__init__.py:2524-2526` - `__subclasscheck__` implementation
- `django/db/models/options.py:246` - validation that raises ValueError
- Test output shows `issubclass(MyBigAutoField, AutoField)` returns False
- `MyBigAutoField in (BigAutoField, SmallAutoField)` returns False (identity check)
- `issubclass(MyBigAutoField, BigAutoField)` returns True (inheritance check)

**Mode:** Abduction (pattern-based diagnosis from code and test output)

**Confidence:** 95% (deduction level - traced through the exact code path)


## Craft Gate Loop - django__django-14238

### Iteration 1: Initial fix drafted and applied

**Drafted fix**: Changed `AutoFieldMeta.__subclasscheck__` at line 2527 in `django/db/models/fields/__init__.py`
- Old: `return subclass in self._subclasses or super().__subclasscheck__(subclass)`
- New: `return issubclass(subclass, self._subclasses) or super().__subclasscheck__(subclass)`

**Codex review**: Approved with improvement suggestion - use `issubclass(subclass, self._subclasses)` instead of `any(issubclass(subclass, cls) for cls in self._subclasses)` since `issubclass()` accepts tuple as second argument. This matches the pattern in `__instancecheck__` and is cleaner.

**Gate result**: ✅ PASS - All 61 tests passed including both FAIL_TO_PASS tests:
- `test_issubclass_of_autofield` (model_fields.test_autofield.AutoFieldInheritanceTests)
- `test_default_auto_field_setting_bigautofield_subclass` (model_options.test_default_pk.TestDefaultPK)

**Resolution**: RESOLVED - The fix changes identity checking to inheritance checking in `__subclasscheck__`, allowing custom subclasses of BigAutoField/SmallAutoField to be recognized as AutoField subclasses.

## Audit - django__django-14238 (2026-05-23)

### Phase 1: Patch verification
✅ Patch is live in container:
- `django/db/models/fields/__init__.py:2527` - `__subclasscheck__` updated from identity check to inheritance check

### Phase 2: Gate execution
Full test suite run: 61 tests executed

### Phase 3: Results classification

#### FAIL_TO_PASS (must all pass)
- ✅ `test_issubclass_of_autofield (model_fields.test_autofield.AutoFieldInheritanceTests)` - PASS
- ✅ `test_default_auto_field_setting_bigautofield_subclass (model_options.test_default_pk.TestDefaultPK)` - PASS

#### PASS_TO_PASS regressions
None - all 59 PASS_TO_PASS tests remain passing

#### Pre-existing failures
None - baseline capture showed all tests passing

### Phase 4: Verdict
- All FAIL_TO_PASS tests: ✅ PASS
- PASS_TO_PASS regressions: ✅ 0
- Contract fulfilled: ✅ YES

**VERDICT: RESOLVED**
**RE-ENTER: none**

The fix correctly changes `AutoFieldMeta.__subclasscheck__` from identity checking (`subclass in self._subclasses`) to inheritance checking (`issubclass(subclass, self._subclasses)`), enabling custom subclasses of BigAutoField/SmallAutoField to be recognized as AutoField subclasses. Zero regressions observed.
