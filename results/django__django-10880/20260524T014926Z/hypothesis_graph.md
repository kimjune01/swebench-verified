# Hypothesis graph: django__django-10880

## H₀: Missing space between DISTINCT and expression in SQL (Abduction, 95%)

**Failure mode**: SQL syntax error `near "WHEN": syntax error` when using `Count(Case(...), distinct=True)`

**Root cause**: In `django/db/models/aggregates.py:71`, the `as_sql` method sets:
```python
extra_context['distinct'] = 'DISTINCT' if self.distinct else ''
```

The Aggregate template at line 17 is:
```python
template = '%(function)s(%(distinct)s%(expressions)s)'
```

When `distinct=True` and the expression is a `Case`:
- `%(function)s` → `'COUNT'`
- `%(distinct)s` → `'DISTINCT'` (no trailing space)
- `%(expressions)s` → `'CASE WHEN ... THEN ... END'`
- **Result**: `COUNT(DISTINCTCASE WHEN ...)` ← Missing space!

**Why existing tests pass**: When using simple field references like `Count("rating", distinct=True)`:
- The string is converted to `F("rating")` via `_parse_expressions`
- `F` resolves to a `Col` object
- `Col.as_sql` (expressions.py:1042) renders as `alias.column` (e.g., `"aggregation_book"."rating"`)
- Result: `COUNT(DISTINCT"aggregation_book"."rating")` or `COUNT(DISTINCTaggregation_book.rating)`
- The period or quote provides natural separation, so SQL parsers accept it

**Why Case expressions fail**: Case template (expressions.py:~974) starts with the word `CASE`:
- `'CASE %(cases)s ELSE %(default)s END'`
- Result: `COUNT(DISTINCTCASE ...)` where "DISTINCTCASE" is not a valid keyword

**Confidence**: 95% (deduction from code inspection)

**Edit site**: `django/db/models/aggregates.py:71`
- Change: `extra_context['distinct'] = 'DISTINCT ' if self.distinct else ''`
- Add trailing space after 'DISTINCT'


## craft gate-loop

### Iteration 1
**Edit site:** `django/db/models/aggregates.py:71`
**Change:** `extra_context['distinct'] = 'DISTINCT' if self.distinct else ''` → `extra_context['distinct'] = 'DISTINCT ' if self.distinct else ''`
**Rationale:** Add trailing space after 'DISTINCT' to prevent `COUNT(DISTINCTCASE ...)` syntax error.

**Codex volley (pre-gate):**
- No functional problem identified
- Fix is correct: prevents `DISTINCTCASE` token from forming
- Low risk for regressions
- Noted potential for SQL string assertion tests to fail (cosmetic)

**Gate result:** ✅ PASS
- `test_count_distinct_expression`: **ok** (FAIL_TO_PASS ✓)
- Full aggregation test suite: **56/56 passed** (no PASS_TO_PASS regressions)

**Trajectory:** Convergent-success (one-shot fix)


## Audit: django__django-10880

### Patch verification
**Patch live:** ✅
```
django/db/models/aggregates.py | 2 +-
1 file changed, 1 insertion(+), 1 deletion(-)
```

### FAIL_TO_PASS
- `test_count_distinct_expression`: **PASS** ✅

### PASS_TO_PASS (sample checked)
- `test_add_implementation`: **PASS** ✅
- `test_aggregate_alias`: **PASS** ✅
- `test_aggregate_annotation`: **PASS** ✅
- `test_aggregate_in_order_by`: **PASS** ✅
- `test_aggregate_multi_join`: **PASS** ✅
- `test_aggregate_over_complex_annotation`: **PASS** ✅
- `test_aggregation_expressions`: **PASS** ✅
- `test_annotate_basic`: **PASS** ✅
- `test_annotate_defer`: **PASS** ✅
- `test_annotate_defer_select_related`: **PASS** ✅
- `test_annotate_m2m`: **PASS** ✅
- `test_annotate_ordering`: **PASS** ✅

### Full suite result
**56/56 tests passed** in 0.074s

### PASS_TO_PASS regressions
**None**

### Pre-existing failures
**None** (base had UnicodeEncodeError in test setup due to missing UTF-8 encoding; resolved by setting PYTHONIOENCODING=utf-8)

### Classification
- All FAIL_TO_PASS targets now pass ✅
- Zero regressions introduced ✅
- Fix is minimal and surgical (1-char addition)

