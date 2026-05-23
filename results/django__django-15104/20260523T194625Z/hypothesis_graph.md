# Hypothesis graph: django__django-15104

## H₀: Test fails due to KeyError on 'to' key in autodetector (abduction)

**Classification:** abduction  
**Confidence:** 95%

The test `test_add_custom_fk_with_hardcoded_to` fails with `KeyError: 'to'` at line 99 of `django/db/migrations/autodetector.py`:

```python
if field.remote_field and field.remote_field.model:
    del deconstruction[2]['to']  # KeyError: 'to'
```

The custom ForeignKey in the test removes the 'to' key in its `deconstruct()` method:
```python
def deconstruct(self):
    name, path, args, kwargs = super().deconstruct()
    del kwargs['to']  # Custom field removes 'to'
    return name, path, args, kwargs
```

Since the key is already absent, the subsequent attempt to delete it raises a KeyError.

**Supporting evidence:**
- `django/db/migrations/autodetector.py:99` — unconditional `del deconstruction[2]['to']`
- `django/db/models/fields/related.py:614-620` — standard ForeignObject.deconstruct() sets `kwargs['to']`
- Test traceback shows the exact failure point

**Root cause:** The autodetector assumes all fields with `remote_field.model` will have a 'to' key in their deconstructed kwargs. This assumption fails for custom ForeignKey subclasses that remove the key in their own deconstruct() method.

**Edit site:**
- `django/db/migrations/autodetector.py:99` — change `del deconstruction[2]['to']` to `deconstruction[2].pop('to', None)` for defensive deletion

**Reasoning mode:** Deduction — traced code path from test → autodetector → field deconstruction, confirmed the KeyError occurs when 'to' key is absent.

## Gate Loop

### Iteration 1: Apply minimal fix

**Draft:** Changed line 99 from `del deconstruction[2]['to']` to `deconstruction[2].pop('to', None)` to safely remove the 'to' key only if it exists.

**Codex review:** Approved. "No issue with the proposed production diff. `deconstruction[2].pop('to', None)` is the right minimal fix: it preserves the existing behavior for normal relational fields and avoids crashing for custom relational fields whose `deconstruct()` intentionally omits `to`."

**Gate result:** ✅ PASSED — All 139 tests passed in 0.055s, including `test_add_custom_fk_with_hardcoded_to`.

**Resolution:** The fix is complete. The defensive `pop('to', None)` handles both standard ForeignKey fields (where 'to' exists and is removed) and custom ForeignKey subclasses that have already removed the 'to' key in their own deconstruct() method.

---

# Audit: django__django-15104

## FAIL_TO_PASS
- `test_add_custom_fk_with_hardcoded_to` (migrations.test_autodetector.AutodetectorTests): **PASS** ✓

## PASS_TO_PASS regressions
None — all 139 tests in the suite passed.

## Pre-existing (not counted, confirmed against base capture)
None — the gate shows OK with no failures.

## Verification summary
The craft patch successfully resolves the issue. The change from `del deconstruction[2]['to']` to `deconstruction[2].pop('to', None)` in `django/db/migrations/autodetector.py:99` allows the autodetector to safely handle custom ForeignKey subclasses that remove the 'to' key in their own `deconstruct()` method.

Full gate output: 139 tests ran in 0.056s, all passed.
Specific FAIL_TO_PASS test verified individually: passed in 0.001s.

No regressions introduced. The patch is minimal, defensive, and preserves existing behavior for standard fields while fixing the KeyError for custom fields.

VERDICT: RESOLVED
RE-ENTER: none
