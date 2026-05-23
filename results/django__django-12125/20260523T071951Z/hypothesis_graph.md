# Hypothesis graph: django__django-12125

## Iteration 1: Initial diagnosis

**H₀ (abduction):** The tests fail because `TypeSerializer.serialize()` uses `__name__` instead of `__qualname__`, causing nested classes to be serialized without their parent class name.

**Evidence:**
- Failing tests expect: `migrations.test_writer.WriterTests.NestedEnum`
- Actual output: `migrations.test_writer.NestedEnum`
- Python `__name__` gives simple name ("NestedEnum"), `__qualname__` gives qualified name ("WriterTests.NestedEnum")
- `TypeSerializer` at django/db/migrations/serializer.py:270,272 uses `self.value.__name__`

**Confidence:** Deduction (~95%) - directly traced the code path and verified with test output

**Edit sites:**
- `django/db/migrations/serializer.py` lines 270, 272: Replace `self.value.__name__` with `self.value.__qualname__`

**Status:** Ready for /craft

## craft gate-loop

### Iteration 1: Applied recon fix
**Change**: Modified `django/db/migrations/serializer.py` lines 270 and 272 in `TypeSerializer.serialize()`:
- Line 270: `self.value.__name__` → `self.value.__qualname__` (builtin types branch)
- Line 272: `self.value.__name__` → `self.value.__qualname__` (non-builtin types branch)

**Rationale**: For nested classes, `__name__` returns only the simple name (e.g., "NestedEnum"), while `__qualname__` returns the qualified name including parent classes (e.g., "WriterTests.NestedEnum"). This matches the pattern already used in `EnumSerializer` and `FunctionTypeSerializer`.

**Gate result**: ✅ PASS — All 47 tests pass, including both FAIL_TO_PASS tests:
- `test_serialize_nested_class (migrations.test_writer.WriterTests)` — PASS
- `test_serialize_numbers (migrations.test_writer.WriterTests)` — PASS

**Status**: RESOLVED in 1 iteration

## Audit: django__django-12125

### FAIL_TO_PASS
- test_serialize_nested_class (migrations.test_writer.WriterTests): ✅ PASS
- test_serialize_numbers (migrations.test_writer.WriterTests): ✅ PASS

### PASS_TO_PASS regressions
None — all 45 PASS_TO_PASS tests remain passing.

### Pre-existing failures
None.

### Gate result
All 47 tests passed. The patch correctly fixes both FAIL_TO_PASS tests without introducing any regressions.

**VERDICT: RESOLVED**
**RE-ENTER: none**
