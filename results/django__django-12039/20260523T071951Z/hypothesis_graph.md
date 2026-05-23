# Hypothesis graph: django__django-12039

## H₀: Baseline Observation (Abduction)
The test `test_descending_columns_list_sql` fails because the CREATE INDEX SQL statement is missing a space between the column name and the DESC keyword.
- Expected: `'("headline" DESC)'`
- Actual: `'CREATE INDEX "whitespace_idx" ON "indexes_article" ("headline"DESC)'`

**Evidence**: Test failure output from gate
**Confidence**: 99% (deduction - observed in test output)

## H₁: Root Cause - Direct String Concatenation in Columns Class (Deduction)

The `Columns.__str__` method in `django/db/backends/ddl_references.py` concatenates column suffixes directly without spacing:

```python
# Line ~88
return self.quote_name(column) + self.col_suffixes[idx]
```

When `col_suffixes[idx]` is `'DESC'`, this produces `"headline"DESC` instead of `"headline" DESC`.

**Evidence**:
- `django/db/backends/ddl_references.py:88` - direct concatenation without space
- `django/db/models/indexes.py:54` - `col_suffixes = [order[1] for order in self.fields_orders]` where order[1] is `'DESC'` or `''`
- Test expects space: `'(%s DESC)' % editor.quote_name('headline')`

**Confidence**: 99% (deduction - traced code path, verified logic)

## H₂: Secondary Issue - Trailing Space in IndexColumns Class (Deduction)

The `IndexColumns.__str__` method always adds a space before col_suffixes, even when empty:

```python
# Line ~115
col = '{} {}'.format(col, self.col_suffixes[idx])
```

When `self.col_suffixes[idx]` is `''` (empty string for ascending order), this produces a trailing space like `"headline" text_pattern_ops ` instead of `"headline" text_pattern_ops"`.

**Evidence**:
- `django/db/backends/ddl_references.py:115` - unconditional space before suffix
- Problem statement: "Note the whitespace after text_pattern_ops"
- Test expects no trailing space: `'(%s text_pattern_ops)' % editor.quote_name('headline')`

**Confidence**: 95% (deduction - traced code path, problem statement confirms)


## Craft iteration 1 - RESOLVED

**Hypothesis**: The `Columns.__str__` and `IndexColumns.__str__` methods concatenate suffixes without proper spacing.

**Edit**: Modified both methods in `django/db/backends/ddl_references.py`:
1. `Columns.__str__` (lines 86-89): Added conditional check - only add space + suffix when suffix is non-empty
2. `IndexColumns.__str__` (lines 113-116): Added conditional check to prevent trailing space when suffix is empty

**Gate result**: GREEN - All 24 tests passed, including `test_descending_columns_list_sql`

**Evidence trajectory**: Convergent success - the FAIL_TO_PASS test now passes without breaking any PASS_TO_PASS tests.

---

# Audit: django__django-12039

## FAIL_TO_PASS
- test_descending_columns_list_sql (indexes.tests.SchemaIndexesTests): **PASS** ✓

## PASS_TO_PASS regressions
None — all 11 PASS_TO_PASS tests remain passing.

## Pre-existing (not counted, confirmed against base capture)
None — the gate is clean.

## Patch Summary
The fix added a space between the column name and suffix (DESC/ASC) in both `Columns.__str__()` and `IndexColumns.__str__()`:
- Before: `self.quote_name(column) + self.col_suffixes[idx]` → `"headline"DESC`
- After: `self.quote_name(column) + ' ' + suffix` (when suffix exists) → `"headline" DESC`

The patch correctly handles the case where the suffix may be empty, avoiding spurious trailing spaces.

## Gate Results
All 24 tests passed (12 skipped as expected for non-applicable databases).

VERDICT: RESOLVED
RE-ENTER: none
