# Hypothesis graph: django__django-12143

## H0: Unescaped regex special characters in formset prefix (abduction, 95%)

**Observation:** Test `test_get_list_editable_queryset_with_regex_chars_in_prefix` fails with `AssertionError: 0 != 1`. The test uses prefix `form$` (contains regex metacharacter `$`) and expects the queryset to contain 1 object but gets 0.

**Root cause:** In `django/contrib/admin/options.py:1634`, the method `_get_edited_object_pks()` builds a regex pattern using string formatting without escaping the `prefix` parameter:

```python
pk_pattern = re.compile(r'{}-\d+-{}$'.format(prefix, self.model._meta.pk.name))
```

When `prefix='form$'` and `pk.name='uuid'`, this creates pattern `r'form$-\d+-uuid$'`. The `$` in `form$` is interpreted as the regex "end of string" anchor, making the pattern impossible to match (nothing can follow end-of-string). The intended key `form$-0-uuid` fails to match, returning an empty list of PKs.

**Fix:** Escape the prefix with `re.escape()`:
```python
pk_pattern = re.compile(r'{}-\d+-{}$'.format(re.escape(prefix), self.model._meta.pk.name))
```

**Confidence:** Deduction — 95%. The code path is direct: test → `_get_list_editable_queryset` → `_get_edited_object_pks` → regex match failure. The regex behavior with unescaped metacharacters is deterministic.

**Supporting evidence:**
- `django/contrib/admin/options.py:1634` — pattern construction without escaping
- `django/contrib/admin/options.py:1635` — pattern used to filter POST keys: `[value for key, value in request.POST.items() if pk_pattern.match(key)]`
- Test POST data includes `'form$-0-uuid': str(a.pk)` which should match but doesn't due to unescaped `$`

**Introduced in:** Commit b18650a263 (Fixed #28462 -- Decreased memory usage with ModelAdmin.list_editable)

---

## Craft gate-loop node 1

**Iteration:** 1  
**Action:** Applied `re.escape()` to both `prefix` and `self.model._meta.pk.name` in `django/contrib/admin/options.py:1634`

**Diff applied:**
```python
# Line 1634
-        pk_pattern = re.compile(r'{}-\d+-{}$'.format(prefix, self.model._meta.pk.name))
+        pk_pattern = re.compile(r'{}-\d+-{}$'.format(re.escape(prefix), re.escape(self.model._meta.pk.name)))
```

**Codex volley:** No functional issues identified. Approved the fix with recommendation to escape both parameters for consistency.

**Gate result:** ✅ PASS  
- All 54 tests passed (OK, skipped=1)
- FAIL_TO_PASS test `test_get_list_editable_queryset_with_regex_chars_in_prefix` now passes

**Trajectory:** Convergent-resolved  
**Resolution:** The recon diagnosis was correct. Escaping regex metacharacters in the prefix parameter fixed the pattern matching issue.

---

## Audit: django__django-12143

**Patch status:** Live (1 file changed, 1 insertion, 1 deletion)

**Gate execution:** All tests passed (54 tests, 0.440s)

### FAIL_TO_PASS
- `test_get_list_editable_queryset_with_regex_chars_in_prefix`: **PASS** ✓

### PASS_TO_PASS regressions
None — all 53 tests that passed on base still pass.

### Pre-existing failures
None confirmed in the test suite.

### Classification
- **FAIL_TO_PASS contract:** Met — the target test now passes
- **PASS_TO_PASS contract:** Met — zero regressions introduced
- **Full contract:** Both conditions satisfied

**VERDICT:** RESOLVED  
**RE-ENTER:** none

