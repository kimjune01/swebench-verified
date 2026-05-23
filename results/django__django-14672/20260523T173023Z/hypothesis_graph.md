# Hypothesis graph: django__django-14672

## H₀: Missing make_hashable on through_fields (abduction, 95%)

**Observation**: Tests fail with `TypeError: unhashable type: 'list'` at `reverse_related.py:139` when hashing `ManyToManyRel.identity`.

**Root cause**: `ManyToManyRel.identity` property (lines 309-314) adds `self.through_fields` directly to the identity tuple. When `through_fields` is a list (e.g., `['event', 'invitee']`), the tuple contains an unhashable element, causing `hash(self.identity)` to fail.

**Evidence**:
- `django/db/models/fields/reverse_related.py:313` — identity includes `self.through_fields` without `make_hashable()`
- `django/db/models/fields/reverse_related.py:124` — parent class uses `make_hashable(self.limit_choices_to)` for the same reason
- `django/utils/hashable.py:17-18` — `make_hashable()` converts lists to tuples
- `tests/m2m_through/models.py:91` — `through_fields=['event', 'invitee']` is defined as a list
- `tests/m2m_through/tests.py` — test expects `hash(reverse_m2m)` to succeed with list through_fields

**Fix**: Wrap `self.through_fields` with `make_hashable()` in `ManyToManyRel.identity` property.

**Edit site**: `django/db/models/fields/reverse_related.py:313`

## Craft gate-loop

### Iteration 1: Draft and volley

**Drafted fix:**
```diff
--- a/django/db/models/fields/reverse_related.py
+++ b/django/db/models/fields/reverse_related.py
@@ -310,7 +310,7 @@
     def identity(self):
         return super().identity + (
             self.through,
-            self.through_fields,
+            make_hashable(self.through_fields),
             self.db_constraint,
         )
```

**codex review:** Confirmed the fix is structurally correct — `make_hashable()` is the right treatment for `through_fields` to prevent `TypeError: unhashable type: 'list'` when `through_fields` is a list. The pattern follows the parent class `ForeignObjectRel` which already uses `make_hashable(self.limit_choices_to)`. codex noted the shown test doesn't directly exercise `through_fields` as a list, but the fix is correct for the stated root cause.

**Applied:** Changed line 313 in `django/db/models/fields/reverse_related.py` from `self.through_fields,` to `make_hashable(self.through_fields),`

### Iteration 1: Gate result

**Status:** ✅ PASS

All 178 tests passed (10 skipped). All FAIL_TO_PASS tests now pass:
- test_multiple_autofields
- test_db_column_clash
- test_ending_with_underscore
- test_including_separator
- test_pk
- test_check_jsonfield
- test_check_jsonfield_required_db_features
- test_ordering_pointing_to_json_field_value
- test_through_fields
- test_reverse_inherited_m2m_with_through_fields_list_hashable

**Resolution:** The recon diagnosis was correct. Wrapping `self.through_fields` with `make_hashable()` in `ManyToManyRel.identity` resolves the `TypeError: unhashable type: 'list'` error when `through_fields` is specified as a list.

---

## Audit: django__django-14672

### Phase 1: Patch verification

Patch is live in the container:
```
 django/db/models/fields/reverse_related.py | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

Change: Line 313 wraps `self.through_fields` with `make_hashable()` to prevent `TypeError: unhashable type: 'list'` when `through_fields` is a list.

### Phase 2: Gate execution

Full gate ran successfully: **178 tests PASSED, 10 skipped, 0 failures**

### Phase 3: Classification

#### FAIL_TO_PASS results

All 8 FAIL_TO_PASS tests now **PASS**:

1. ✅ `test_multiple_autofields (invalid_models_tests.test_models.MultipleAutoFieldsTests)` — PASS
2. ✅ `test_db_column_clash (invalid_models_tests.test_models.FieldNamesTests)` — PASS
3. ✅ `test_ending_with_underscore (invalid_models_tests.test_models.FieldNamesTests)` — PASS
4. ✅ `test_including_separator (invalid_models_tests.test_models.FieldNamesTests)` — PASS
5. ✅ `test_pk (invalid_models_tests.test_models.FieldNamesTests)` — PASS
6. ✅ `test_check_jsonfield (invalid_models_tests.test_models.JSONFieldTests)` — PASS
7. ✅ `test_check_jsonfield_required_db_features (invalid_models_tests.test_models.JSONFieldTests)` — PASS
8. ✅ `test_ordering_pointing_to_json_field_value (invalid_models_tests.test_models.JSONFieldTests)` — PASS

#### PASS_TO_PASS regressions

**None.** The PASS_TO_PASS list is empty, and all 178 tests in the full suite passed with no failures.

#### Pre-existing failures

**None.** All tests pass cleanly.

The fail-on-base capture shows the test suite crashed before running tests due to the unhashable type error. The fix resolves this, allowing the full suite to run and pass.

### Phase 4: Verdict

**Contract fulfilled:**
- ✅ All FAIL_TO_PASS tests now pass (8/8)
- ✅ Zero PASS_TO_PASS regressions
- ✅ Surgical fix: 1 line changed, wraps `through_fields` with `make_hashable()`
- ✅ Follows existing pattern from parent class `ForeignObjectRel.identity` (line 124)

The recon diagnosis was accurate: `ManyToManyRel.identity` needed `make_hashable()` around `self.through_fields` to handle the case where `through_fields` is specified as a list rather than a tuple.
