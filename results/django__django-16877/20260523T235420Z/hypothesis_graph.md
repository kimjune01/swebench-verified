# Hypothesis graph: django__django-16877

## H₀: Missing filter implementation (abduction → deduction)

**Status**: Root cause identified  
**Confidence**: 99% (deduction)  
**Mode**: Traced error to missing registration

The tests fail with `TemplateSyntaxError: Invalid filter: 'escapeseq'` because the filter is not registered in Django's template system.

**Evidence trail**:
1. Error originates in `/testbed/django/template/base.py:603` in `find_filter()` 
2. Template filters are defined in `django/template/defaultfilters.py`
3. Related filter `safeseq` exists at line 492, marks sequence items as safe
4. No `escapeseq` filter exists in the codebase (grepped entire repo)

**Expected behavior** (from tests):
- `escapeseq` should escape each item in a sequence
- Already-safe items (marked with `mark_safe()`) should remain safe
- Must work identically whether autoescape is on or off
- Example: `["x&y", "<p>"] → ["x&amp;y", "&lt;p&gt;"]`
- Example: `[mark_safe("x&y")] → [mark_safe("x&y")]` (unchanged)

**Implementation pattern**:
- Mirror `safeseq` structure but use `conditional_escape()` instead of `mark_safe()`
- `conditional_escape()` respects `__html__()` method (SafeData), escapes otherwise
- Register with `@register.filter(is_safe=True)` (output is properly escaped)

**Supporting code**:
- `django/template/defaultfilters.py:492` — `safeseq` implementation
- `django/template/defaultfilters.py:17` — imports `conditional_escape`
- `django/template/defaultfilters.py:347` — `escape_filter` uses same pattern


## Craft Loop Node 1 - Implementation (RESOLVED)

**Action**: Implemented `escapeseq` filter in `django/template/defaultfilters.py` after line 500 (immediately following `safeseq`).

**Implementation**:
```python
@register.filter(is_safe=True)
def escapeseq(value):
    """
    Escape each element in the sequence individually. Return a list with the
    results.
    """
    return [conditional_escape(obj) for obj in value]
```

**Codex review feedback**: 
- Implementation functionally correct
- Suggested improving docstring from "A 'safe' filter" (misleading, copied from safeseq) to direct description
- Applied: cleaner docstring without "safe" terminology since this filter escapes rather than marks safe

**Gate result**: ✅ GREEN - All 4 FAIL_TO_PASS tests pass:
- test_autoescape_off: ok
- test_basic: ok
- test_chain_join: ok
- test_chain_join_autoescape_off: ok

**Trajectory**: Convergent (direct resolution on first iteration)

**Resolution**: The `conditional_escape()` function correctly handles both escaping unsafe strings (`&` → `&amp;`, `<` → `&lt;`) and preserving already-safe `SafeData` objects, working identically regardless of autoescape context.


## Audit: django__django-16877

**Patch verification**: 9 lines added to `django/template/defaultfilters.py`

### FAIL_TO_PASS
- test_autoescape_off: ✅ PASS
- test_basic: ✅ PASS
- test_chain_join: ✅ PASS
- test_chain_join_autoescape_off: ✅ PASS

### PASS_TO_PASS regressions
None (no PASS_TO_PASS tests specified)

### Pre-existing failures (not counted)
None

### Contract verification
✅ All 4 FAIL_TO_PASS tests pass  
✅ Zero regressions  
✅ Full contract satisfied

**Gate output**: All tests completed successfully in 0.003s
