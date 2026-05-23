# Hypothesis graph: django__django-11211

## H1: Type mismatch in GFK prefetch key comparison (ACTIVE)

**Reasoning mode:** Deduction
**Confidence:** 98%

**Failure symptom:**
Test `test_prefetch_GFK_uuid_pk` fails with:
- Expected: `[<Article: Article object (18bd470c-...)>]`
- Got: `[None]`

When prefetching a GenericForeignKey pointing to a model with UUID primary key, the related object is not properly matched and returns None.

**Root cause:**
In `django/contrib/contenttypes/fields.py:205`, the `gfk_key` function uses `get_prep_value` to convert the stored foreign key value:
```python
return (model._meta.pk.get_prep_value(getattr(obj, self.fk_field)), model)
```

For UUID primary keys:
1. The fk_field (`object_pk_uuid`) is a TextField that stores the UUID as a string
2. `get_prep_value` doesn't convert the string back to a UUID object - it returns the string as-is
3. The comparison key becomes `(string, Article)` 
4. But the related object's key is `(UUID_object, Article)` from line 209
5. Since `"uuid-string" != uuid.UUID("uuid-string")`, the matching fails

**Evidence:**
- Line 232 in the same file uses `to_python` for the same purpose: `rel_obj._meta.pk.to_python(pk_val) == rel_obj.pk`
- Line 575 in GenericRelation also uses `to_python`: `object_id_converter = instances[0]._meta.pk.to_python`
- Test shows `str(uuid_obj) == uuid_obj` evaluates to `False`

**Edit site:**
- `django/contrib/contenttypes/fields.py` line 205: Change `get_prep_value` to `to_python`

This converts the stored string value back to the proper Python type (UUID object) before comparison, matching the pattern used elsewhere in the same file.

## Gate iteration 1 (RESOLVED)

**Change applied:**
```diff
--- a/django/contrib/contenttypes/fields.py
+++ b/django/contrib/contenttypes/fields.py
@@ -202,7 +202,7 @@ class GenericForeignKey(FieldCacheMixin):
             else:
                 model = self.get_content_type(id=ct_id,
                                               using=obj._state.db).model_class()
-                return (model._meta.pk.get_prep_value(getattr(obj, self.fk_field)),
+                return (model._meta.pk.to_python(getattr(obj, self.fk_field)),
                         model)
```

**Codex review:** Confirmed the fix is correct. `get_prep_value()` is the wrong normalizer for the prefetch join key - the related-object side uses the Python pk value (UUID), while the GFK instance side holds the raw stored value (str from TextField). `to_python()` is the correct conversion for comparing against `obj.pk` in memory.

**Gate result:** ✅ PASS - All 77 tests passed, including `test_prefetch_GFK_uuid_pk`

**Trajectory:** Convergent (resolution) - the fix addresses the root cause exactly as diagnosed by recon. The UUID string is now properly converted to a UUID object before comparison, matching the pattern used elsewhere in the same file (lines 232, 575).

## Audit: django__django-11211

**Patch status:** Live (1 file changed, 1 insertion, 1 deletion)

**Gate execution:** Ran 77 tests in 0.235s — OK

### FAIL_TO_PASS
- `test_prefetch_GFK_uuid_pk (prefetch_related.tests.GenericRelationTests)`: ✅ PASS
  - Base: FAIL with `AssertionError: Lists differ: [None] != [<Article: ...>]`
  - Now: PASS

### PASS_TO_PASS regressions
None — all 77 tests passed.

### Pre-existing failures (not counted)
None — the only failure on base was the FAIL_TO_PASS test itself.

### Verdict
All FAIL_TO_PASS tests now pass with zero regressions. The fix correctly converts UUID strings to UUID objects using `to_python()` instead of `get_prep_value()`, enabling proper key matching in GenericForeignKey prefetch operations.

VERDICT: RESOLVED
RE-ENTER: none
