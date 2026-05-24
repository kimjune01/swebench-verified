# Hypothesis graph: django__django-17087

## H₀ (Initial abduction)
**Status**: Confirmed via code trace → promoting to root cause
**Mode**: Deduction (95%)

The test fails because `FunctionTypeSerializer.serialize()` constructs the qualified path for class methods using `klass.__name__` instead of `klass.__qualname__`. For nested classes, `__name__` returns only the simple class name (e.g., "NestedChoices"), while `__qualname__` returns the full qualified name including outer classes (e.g., "WriterTests.NestedChoices").

**Evidence**:
- Test output shows: expected `'migrations.test_writer.WriterTests.NestedChoices.method'` but got `'migrations.test_writer.NestedChoices.method'`
- Line 171 of `django/db/migrations/serializer.py` uses `klass.__name__` 
- Python inspection confirms: `Inner.__name__` = "Inner", `Inner.__qualname__` = "Outer.Inner"
- Line 182 (non-class-method path) correctly uses `self.value.__qualname__`
- The TypeSerializer (for classes, not methods) already correctly uses `__qualname__` (line 421)

**Edit site**:
- `django/db/migrations/serializer.py:171` - Replace `klass.__name__` with `klass.__qualname__`

**Supporting code**:
```python
# Line 171 (BUGGY):
return "%s.%s.%s" % (module, klass.__name__, self.value.__name__), {
    "import %s" % module
}
# Should be:
return "%s.%s.%s" % (module, klass.__qualname__, self.value.__name__), {
    "import %s" % module
}
```


## Craft Gate Loop

### Iteration 1: Initial Fix

**Change Applied:**
- `django/db/migrations/serializer.py:171` - Changed `klass.__name__` to `klass.__qualname__`

**Codex Pre-Gate Review:**
- Confirmed fix is correct: `__name__` drops containing classes, `__qualname__` preserves the full nesting hierarchy
- For non-nested classes, `__name__ == __qualname__`, so existing behavior unchanged
- Noted edge case with `<locals>` in `__qualname__`, but acceptable for migrations context

**Gate Result:** ✅ PASS
- All 54 tests passed
- `test_serialize_nested_class_method` now passes with correct serialization: `migrations.test_writer.WriterTests.NestedChoices.method`
- No regressions detected

**Resolution:** The single-line fix correctly addresses the root cause. The FunctionTypeSerializer now uses `klass.__qualname__` to preserve the full qualified name including parent classes for nested class methods.

---

## Audit: django__django-17087

### Patch Verification
**Patch Status:** Live in tree
- `django/db/migrations/serializer.py | 2 +-` (1 insertion, 1 deletion)

### FAIL_TO_PASS Results
- `test_serialize_nested_class_method` (migrations.test_writer.WriterTests): **PASS** ✅

### PASS_TO_PASS Results
All 54 tests passed. No regressions detected.

### Pre-existing Failures
None.

### Final Verdict
- All FAIL_TO_PASS tests pass: ✅
- Zero PASS_TO_PASS regressions: ✅
- Contract fulfilled: The fix correctly serializes nested class methods using `__qualname__` instead of `__name__`, preserving the full qualified path including parent classes.

VERDICT: RESOLVED
RE-ENTER: none
