# Hypothesis graph: django__django-12325

## H1: parent_links collection doesn't filter by parent_link=True

**Type:** Root cause (abduction → deduction, confidence: 95%)

**Evidence:**
- `django/db/models/base.py:204-207` collects ALL OneToOneFields into `parent_links` dict, regardless of `parent_link` attribute
- Code: `if isinstance(field, OneToOneField):` without checking `field.remote_field.parent_link`
- When multiple OneToOneFields point to same parent model, last one overwrites in dict
- Later at `options.py:255`, code checks `if not field.remote_field.parent_link:` and raises ImproperlyConfigured
- Stack trace confirms: error raised at `options.py:256` during `_prepare()`

**Why this causes the failure:**
1. `ParkingLot(Place)` with `other_place = OneToOneField(Place)` (no parent_link=True)
2. During class creation, `other_place` is added to `parent_links[Place]`
3. Auto-generated `place_ptr` field would normally be created, but since `parent_links[Place]` already exists, it's skipped
4. `other_place` is used as the parent link field (line 245 in options.py: `field = next(iter(self.parents.values()))`)
5. Check at line 255 fails because `other_place.remote_field.parent_link` is False

**Edit site:**
- `django/db/models/base.py` lines 205-207: Add condition `and field.remote_field.parent_link` to the if statement

**Rejected alternatives:**
- Could fix by changing order checking in options.py, but that doesn't address root cause of collecting wrong fields
- Could auto-set parent_link on collected fields, but that violates explicit user intent

## Craft gate loop

### Iteration 1: Apply H1 fix

**Change applied:**
- `django/db/models/base.py:205`: Changed condition from `if isinstance(field, OneToOneField):` to `if isinstance(field, OneToOneField) and field.remote_field.parent_link:`
- `django/db/models/base.py:203`: Updated comment to "Locate OneToOneField instances with parent_link=True."

**codex volley (pre-gate):**
Confirmed fix is "directionally correct" - filtering parent_links to only fields with parent_link=True prevents user-defined OneToOneFields from being misidentified as MTI parent links. Suggested updating comment, which was incorporated.

**Gate result:** ✅ PASS
- All 205 tests passed (OK, skipped=2)
- FAIL_TO_PASS tests now pass:
  - `test_onetoone_with_parent_model` ✅
  - `test_clash_parent_link` ✅

**Trajectory:** Convergent-resolved on first iteration.

**Resolution:** The recon diagnosis was correct. The single-line fix (adding parent_link filter) allows Django to properly distinguish between user-defined OneToOneFields and actual parent links, enabling auto-generation of parent_ptr when needed.

---

## Audit: django__django-12325

**Patch confirmed live:**
```
django/db/models/base.py | 4 ++--
1 file changed, 2 insertions(+), 2 deletions(-)
```

### FAIL_TO_PASS
- test_clash_parent_link (invalid_models_tests.test_relative_fields.ComplexClashTests): **PASS** ✓
- test_onetoone_with_parent_model (invalid_models_tests.test_models.OtherModelTests): **PASS** ✓

### PASS_TO_PASS regressions
None. All 205 tests passed (OK, skipped=2).

### Pre-existing failures (not counted, confirmed against base capture)
None.

### Gate output summary
```
Ran 205 tests in 0.220s
OK (skipped=2)
```

All tests in the suite passed. Both required FAIL_TO_PASS tests now pass. Zero regressions introduced.
