# Hypothesis graph: django__django-13033

---

## Hypothesis Node: django__django-13033 (Initial Diagnosis)

**Timestamp:** 2026-05-23  
**Type:** abduction → deduction  
**Confidence:** 99%

### Symptom

Test `test_order_by_self_referential_fk` fails with wrong ordering when using `order_by('author__editor_id')` on a self-referential FK. Expected `['Article 1', 'Article 2']` but got `['Article 2', 'Article 1']`.

### Root Cause

File: `django/db/models/sql/compiler.py:730`

The condition that determines whether to apply a related model's default ordering compares the full lookup path to `field.attname`:

```python
if field.is_relation and opts.ordering and getattr(field, 'attname', None) != name and name != 'pk':
```

When `name = 'author__editor_id'` and `field.attname = 'editor_id'`, the comparison is True (they don't match), so the default ordering is incorrectly applied.

### Fix Specification

Change line 730 to compare only the last component of the path:

```python
if field.is_relation and opts.ordering and getattr(field, 'attname', None) != pieces[-1] and pieces[-1] != 'pk':
```

This makes the behavior consistent with direct FK attname references (issue #19195).

### Evidence

1. `compiler.py:724` splits the path: `pieces = name.split(LOOKUP_SEP)`
2. Line 730 uses `name` instead of `pieces[-1]` in comparison
3. Existing test `test_order_by_fk_attname` (line 325) confirms attname ordering should skip default ordering
4. Manual trace confirms: `'editor_id' != 'author__editor_id'` is True (bug), but `'editor_id' != 'editor_id'` is False (correct)

### Prediction

Changing the comparison to use `pieces[-1]` will:
- Fix the failing test
- Make traversed FK attname ordering (`author__editor_id`) behave like direct FK attname ordering (`author_id`)
- Not break any existing functionality since direct references already work correctly


## craft gate-loop iteration 1

**Hypothesis**: Line 730 in `django/db/models/sql/compiler.py` incorrectly compares full lookup path to `field.attname` instead of last component.

**Fix applied**: Changed line 730 from:
```python
if field.is_relation and opts.ordering and getattr(field, 'attname', None) != name and name != 'pk':
```
to:
```python
if field.is_relation and opts.ordering and getattr(field, 'attname', None) != pieces[-1] and pieces[-1] != 'pk':
```

**codex review**: Confirmed fix is correct. Both parts of the condition needed the change (attname comparison and pk comparison). Low breakage risk.

**Gate outcome**: GREEN - all 27 tests passed, including `test_order_by_self_referential_fk` (FAIL_TO_PASS).

**E-value trajectory**: Convergent success - single iteration to resolution.

---

## Audit: django__django-13033

### FAIL_TO_PASS
- `test_order_by_self_referential_fk`: **PASS** ✓

### PASS_TO_PASS regressions
None — all 27 tests in the suite passed.

### Pre-existing (not counted, confirmed against base capture)
None.

### Result
All FAIL_TO_PASS tests now pass. Zero regressions. The fix correctly handles self-referential FK ordering with attname suffixes by comparing `pieces[-1]` (the final path component) rather than the full lookup path, making traversed FK attname ordering behave consistently with direct FK attname ordering.
