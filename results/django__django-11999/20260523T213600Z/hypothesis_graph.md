# Hypothesis graph: django__django-11999

## H₀: Initial observation (abduction)
The test `test_overriding_FIELD_display` fails because `get_foo_bar_display()` returns 'foo' (the choice display value) instead of 'something' (the custom override).

**Evidence**: Test failure output shows `AssertionError: 'foo' != 'something'`

## H₁: Root cause - unconditional setattr in Field.contribute_to_class (deduction, 99%)
Django unconditionally overwrites `get_FOO_display()` methods in `Field.contribute_to_class()` when a field has choices.

**Location**: `django/db/models/fields/__init__.py:766-767`

**Code**:
```python
if self.choices is not None:
    setattr(cls, 'get_%s_display' % self.name,
            partialmethod(cls._get_FIELD_display, field=self))
```

**Why this is the root cause**:
1. `setattr()` unconditionally replaces any existing attribute with that name
2. Custom `get_FOO_display()` methods defined in the model class are overwritten when the field's `contribute_to_class()` is called during model construction
3. The descriptor check on lines 763-764 uses `if not getattr(cls, self.attname, None):` before setting, but the `get_FOO_display` setter has no such guard

**Supporting evidence**:
- Direct test: Python REPL confirms `setattr()` overwrites custom methods
- Code inspection: Only one location sets `get_FOO_display` (verified by grep)
- Pattern: The descriptor setting (lines 763-764) already has the guard pattern that should be applied here

**Fix**: Add a guard to check if the method already exists before setting it, matching the pattern used for the descriptor.

## Rejected hypotheses
None - the root cause is clear from code inspection and confirmed by direct testing.

## Craft: Gate Loop - Iteration 1

**Drafted fix:** Added guard check using `cls.__dict__` to preserve custom `get_FIELD_display()` methods.

**codex volley 1 (pre-gate):** Flagged that using `getattr(cls, name, None)` would be too broad - it would also find inherited methods from base classes, which could break field inheritance when a subclass overrides a field with different choices. Recommended using `'get_%s_display' % self.name not in cls.__dict__` instead to only check if the method is defined directly on the class.

**Revision:** Applied codex's recommendation - changed from `getattr()` check to `cls.__dict__` check.

**Applied diff:**
```diff
--- a/django/db/models/fields/__init__.py
+++ b/django/db/models/fields/__init__.py
@@ -763,8 +763,9 @@ class Field(RegisterLookupMixin):
             if not getattr(cls, self.attname, None):
                 setattr(cls, self.attname, self.descriptor_class(self))
         if self.choices is not None:
-            setattr(cls, 'get_%s_display' % self.name,
-                    partialmethod(cls._get_FIELD_display, field=self))
+            if 'get_%s_display' % self.name not in cls.__dict__:
+                setattr(cls, 'get_%s_display' % self.name,
+                        partialmethod(cls._get_FIELD_display, field=self))
```

**Gate result:** ✅ PASS - All 31 tests passed, including `test_overriding_FIELD_display`.

**Trajectory:** Convergent-success (first iteration green).

## Audit: django__django-11999

### FAIL_TO_PASS
- test_overriding_FIELD_display (model_fields.tests.GetFieldDisplayTests): **PASS** ✅

### PASS_TO_PASS regressions
None - all 30 PASS_TO_PASS tests remain passing.

### Pre-existing failures (not counted)
None confirmed.

### Gate summary
Ran 31 tests in 0.008s - **OK**

All FAIL_TO_PASS tests now pass, zero regressions introduced. The fix successfully preserves custom `get_FIELD_display()` methods by checking `cls.__dict__` before setting the auto-generated method.

VERDICT: RESOLVED
RE-ENTER: none
