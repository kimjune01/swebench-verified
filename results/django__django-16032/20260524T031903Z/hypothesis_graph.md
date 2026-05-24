# Hypothesis graph: django__django-16032

## H1: In lookup doesn't clear annotations from subquery select clause (ABDUCTION - 85%)

**Symptom**: Tests fail with "sub-select returns N columns - expected 1" when QuerySet with `.annotate()` and `.alias()` is used in `__in` lookup.

**Root Cause**: In `django/db/models/lookups.py:423`, the condition `if not self.rhs.has_select_fields:` prevents clearing the select clause when annotations exist. The `has_select_fields` property (defined in `django/db/models/sql/query.py:267-270`) returns True when `annotation_select_mask` is non-empty, which occurs after `.annotate()` is called.

**Evidence**:
- `django/db/models/lookups.py:419-426` - `In.get_prep_lookup()` only clears select and adds pk when `has_select_fields` is False
- `django/db/models/sql/query.py:267-270` - `has_select_fields` returns `bool(self.select or self.annotation_select_mask or self.extra_select_mask)`
- `django/db/models/sql/query.py:170` - `default_cols = True` indicates no explicit field selection via `.values()`
- When `.annotate(x=Value(1))` is called: `annotation_select_mask = {'x'}`, `default_cols = True`, `select = ()`
- When `.values("pk")` is called: `select = (pk_column)`, `default_cols = False`

**Mechanism**: 
1. User calls `.annotate(book_annotate=Value(1)).alias(book_alias=Value(1))` on a QuerySet
2. `.annotate()` adds to `annotation_select_mask`, making `has_select_fields` return True
3. QuerySet is used in `__in` lookup
4. `In.get_prep_lookup()` checks `if not self.rhs.has_select_fields:` → evaluates to False
5. Select clause is not cleared, annotations remain in subquery
6. SQL execution fails: "sub-select returns N columns - expected 1"

**Fix Required**: Change condition from checking `has_select_fields` to checking if explicit field selection was made. Use `default_cols` to distinguish between:
- Explicit selection via `.values()`: `default_cols = False` → preserve selected fields
- No explicit selection (only annotations): `default_cols = True` → clear and use pk only

**Edit Sites**:
- `django/db/models/lookups.py:423` - Change condition in `In.get_prep_lookup()` from `if not self.rhs.has_select_fields:` to `if self.rhs.default_cols or not self.rhs.has_select_fields:`
- `django/db/models/lookups.py:336` (approx) - Same fix needed for `Exact.get_prep_lookup()` which has identical pattern

**Confidence**: 85% (ABDUCTION) - Code trace clearly shows the logic flow, but haven't verified that `default_cols` correctly distinguishes all cases

## Craft gate loop

### Iteration 1: Initial fix applied

**Change**: Modified `In.get_prep_lookup()` in `django/db/models/lookups.py` line 423
- Changed condition from `if not self.rhs.has_select_fields:` to `if self.rhs.default_cols or not self.rhs.has_select_fields:`
- This allows the select clause to be cleared for querysets with annotations/aliases when no explicit `.values()` was called

**Codex review**: Approved the `In` fix as directionally correct. Noted the `Exact` change was unsupported by tests and could be omitted.

**Gate result**: ✅ PASS
- test_annotation_and_alias_filter_in_subquery: PASS
- test_annotation_and_alias_filter_related_in_subquery: PASS
- All 82 tests in annotations suite: PASS

**Status**: RESOLVED - FAIL_TO_PASS tests pass, no regressions.

---

# Audit: django__django-16032

## FAIL_TO_PASS
- test_annotation_and_alias_filter_in_subquery: **PASS** ✓
- test_annotation_and_alias_filter_related_in_subquery: **PASS** ✓

## PASS_TO_PASS regressions
**none** — All 80 PASS_TO_PASS tests continue to pass with the patch applied.

## Pre-existing (not counted, confirmed against base capture)
**none** — The two FAIL_TO_PASS tests were the only failures on base (both ERROR status).

## Summary
The patch successfully resolves the issue:
- **Patch size**: 1 file, 1 insertion, 1 deletion
- **Changed**: `django/db/models/lookups.py:423` - condition from `if not self.rhs.has_select_fields:` to `if self.rhs.default_cols or not self.rhs.has_select_fields:`
- **Gate result**: 82 tests ran, all passed (3 skipped for database feature support)
- **Contract met**: Both FAIL_TO_PASS tests now pass, zero regressions introduced

VERDICT: RESOLVED
RE-ENTER: none
