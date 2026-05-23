# Hypothesis graph: django__django-16938

## H₀ (2026-05-23, abduction, confidence: 90%)

**Failure**: Tests fail with `FieldError: Field Topic.category cannot be both deferred and traversed using select_related at the same time.`

**Root cause**: The serializer optimization (commit 19e0587ee5, Sept 2022) added `.only("pk")` to m2m querysets to reduce data fetching. However, when the m2m related model has a custom manager with `select_related()`, this creates a conflict:
- The custom manager's `select_related("category")` requests eager loading of the category field
- The serializer's `.only("pk")` defers all fields except pk (including category)
- The validation check added in commit b3db6c8dcb (Aug 2022) raises an error for this contradiction

**Evidence**:
- `django/core/serializers/python.py:82`: `return getattr(obj, field.name).only("pk").iterator()`
- `django/db/models/fields/related_descriptors.py:964`: M2M manager uses `related_model._default_manager.__class__` as superclass
- `tests/serializers/models/base.py`: TopicManager.get_queryset() returns `super().get_queryset().select_related("category")`
- `django/db/models/query_utils.py:347`: Error raised when field is in both select_related and deferred set

**Call path**:
1. Serializer calls `handle_m2m_field()` for Article.topics
2. Gets m2m queryset via `getattr(article, "topics")` → ManyRelatedManager
3. ManyRelatedManager inherits from TopicManager (the _default_manager)
4. TopicManager.get_queryset() adds `.select_related("category")`
5. Serializer adds `.only("pk")` → queryset has both select_related("category") and only("pk")
6. During query execution, `select_related_descend()` validates that category is not in the deferred set
7. Error: category is in select_related but not in only("pk") mask

**Fix**: Clear select_related before applying only("pk") by calling `.select_related(None)` first.

**Edit sites**:
1. `django/core/serializers/python.py:82` - Change `.only("pk")` to `.select_related(None).only("pk")`
2. `django/core/serializers/xml_serializer.py:158` - Change `.only("pk")` to `.select_related(None).only("pk")`

**Justification**: The serializer only needs pk values for m2m relations. Any select_related from custom managers is irrelevant and should be cleared to avoid the conflict. The `select_related(None)` call explicitly clears the select_related list (per QuerySet.select_related docstring).


## Gate Loop - Iteration 1

**Fix Applied:**
- `django/core/serializers/python.py` line 82: Added `.select_related(None)` before `.only("pk")` to clear manager-inherited select_related
- `django/core/serializers/xml_serializer.py` line 158: Same fix for XML serializer
- Both with proper multi-line formatting per Django style

**Codex Review:** 
- Confirmed fix is directionally correct
- No functional issues identified
- Noted that `select_related()` was unnecessary overhead anyway since only PKs are serialized
- Suggested line wrapping (applied)

**Gate Result:** ✅ GREEN
- All 135 tests passed in 0.227s
- All FAIL_TO_PASS tests now pass
- No regressions detected

**Resolution:** The fix successfully resolves the conflict between `.only("pk")` optimization and custom manager's `select_related()`. By clearing select_related before applying only(), we avoid the "Field cannot be both deferred and traversed using select_related at the same time" error.
# Audit: django__django-16938

## Patch Applied
- django/core/serializers/python.py: Added .select_related(None) before .only("pk") in M2M serialization
- django/core/serializers/xml_serializer.py: Added .select_related(None) before .only("pk") in M2M serialization

## Gate Results
All 135 tests passed.

## FAIL_TO_PASS (all must pass)
✓ test_altering_serialized_output (JSON/XML/YAML) - "The ability to create new objects by modifying serialized content." - PASS
✓ test_deserialize_force_insert (JSON/XML/YAML) - "Deserialized content can be saved with force_insert as a parameter." - PASS
✓ test_deterministic_mapping_ordering (JSON/XML/YAML) - "Mapping such as fields should be deterministically ordered. (#24558)" - PASS
✓ test_pre_1000ad_date (JSON/XML/YAML) - "Year values before 1000AD are properly formatted" - PASS
✓ test_serialize (JSON/XML/YAML) - "Basic serialization works." - PASS
✓ test_serialize_no_only_pk_with_natural_keys (serializers.test_json.JsonSerializerTestCase) - PASS
✓ test_serialize_only_pk (serializers.test_json.JsonSerializerTestCase) - PASS
✓ test_serialize_prefetch_related_m2m (serializers.test_json.JsonSerializerTestCase) - PASS
✓ test_serialize_progressbar (serializers.test_json.JsonSerializerTestCase) - PASS

All 9 FAIL_TO_PASS tests now PASS.

## PASS_TO_PASS regressions
None - all 135 tests passed, including:
✓ test_stream_class (serializers.tests.SerializerAPITests.test_stream_class)
✓ test_lazy_string_encoding (serializers.test_json.DjangoJSONEncoderTests.test_lazy_string_encoding)
✓ test_timedelta (serializers.test_json.DjangoJSONEncoderTests.test_timedelta)
✓ test_deserializer_pyyaml_error_message (serializers.test_yaml.NoYamlSerializerTestCase)
✓ test_dumpdata_pyyaml_error_message (serializers.test_yaml.NoYamlSerializerTestCase)
✓ test_serializer_pyyaml_error_message (serializers.test_yaml.NoYamlSerializerTestCase)
✓ test_builtin_serializers (serializers.tests.SerializerRegistrationTests)
✓ test_get_unknown_deserializer (serializers.tests.SerializerRegistrationTests)
✓ And all other tests

## Pre-existing failures (confirmed against base capture)
None applicable - the base capture showed failures in:
- test_serialize_progressbar (YAML) with FieldError about Topic.category select_related/defer conflict
But this test now PASSES with the patch.

## Analysis
The patch successfully resolves the core issue: when serializing M2M fields using `.only("pk")`, any inherited `select_related()` configuration was causing a conflict with the deferred fields. The fix clears inherited select_related with `.select_related(None)` before applying `.only("pk")`.

This prevents the "Field cannot be both deferred and traversed using select_related at the same time" error that was occurring when serializing objects with prefetched M2M relationships.

VERDICT: RESOLVED
RE-ENTER: none
