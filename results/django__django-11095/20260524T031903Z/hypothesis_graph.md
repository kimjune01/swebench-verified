# Hypothesis graph: django__django-11095

## H₀ (abduction, 2026-05-23)
**The tests fail because `get_inline_instances()` directly accesses `self.inlines` instead of calling a `get_inlines()` hook.**

Evidence:
- Test defines custom `get_inlines(request, obj)` that returns `[]` when `request.name` is unset
- Test expects `get_inline_instances(request)` to return `[]` when `get_inlines()` returns `[]`
- Actual result: `get_inline_instances()` returns 2 inline instances (both AlternateInline and MediaInline)
- Code inspection shows `get_inline_instances()` at `django/contrib/admin/options.py:585` uses `for inline_class in self.inlines:` directly
- No `get_inlines()` method exists in ModelAdmin class

Root cause: Missing hook method + direct attribute access in `get_inline_instances()`

Edit sites:
1. Add `get_inlines(self, request, obj=None)` method (insert before `get_inline_instances`, around line 583)
2. Update `get_inline_instances()` line 585: change `self.inlines` to `self.get_inlines(request, obj)`

Confidence: deduction — 98% (traced code path, identified exact line, pattern matches existing hooks like `get_readonly_fields`)

## Gate Loop - Iteration 1 (RESOLVED)

**Hypothesis**: Add `get_inlines(request, obj=None)` hook method and update `get_inline_instances()` to call it instead of directly accessing `self.inlines`.

**Implementation**:
1. Added `get_inlines(self, request, obj=None)` method at line 583 in `django/contrib/admin/options.py`:
   - Returns `self.inlines` (following pattern of `get_readonly_fields` and `get_prepopulated_fields`)
   - Includes docstring: "Hook for specifying custom inlines."
2. Updated `get_inline_instances()` at line 591 to call `self.get_inlines(request, obj)` instead of `self.inlines`

**Codex Review**: No obvious functional bugs. Patch is the right minimal implementation. Confirmed it fixes the root cause.

**Gate Result**: ✅ PASS
- All 20 tests passed, including `test_get_inline_instances_override_get_inlines`
- No regressions

**Trajectory**: Convergent (resolved on first iteration)

**Resolution**: The fix allows `ModelAdmin` subclasses to override `get_inlines()` to dynamically select inlines based on request or object state, which is exactly what the failing test expected.

---

# Audit: django__django-11095

## FAIL_TO_PASS
- test_get_inline_instances_override_get_inlines: **PASS** ✓

## PASS_TO_PASS regressions
**None** — all 19 PASS_TO_PASS tests remain passing:
- test_no_deletion: ok
- test_custom_form_meta_exclude: ok
- test_custom_form_meta_exclude_with_readonly: ok
- test_get_fieldsets: ok
- test_get_formset_kwargs: ok
- test_get_formsets_with_inlines_returns_tuples: ok
- test_extra_param: ok
- test_get_extra: ok
- test_get_max_num: ok
- test_get_min_num: ok
- test_max_num_param: ok
- test_min_num_param: ok
- test_no_param: ok
- test_basic_add_GET: ok
- test_basic_add_POST: ok
- test_basic_edit_GET: ok
- test_basic_edit_POST: ok
- test_add: ok
- test_delete: ok

## Pre-existing (not counted, confirmed against base capture)
**None** — the only failure on base was `test_get_inline_instances_override_get_inlines`, which is now fixed.

## Patch Analysis
The craft patch successfully implements the required hook:
1. Added `get_inlines(request, obj=None)` method returning `self.inlines`
2. Updated `get_inline_instances()` to call `self.get_inlines(request, obj)` instead of directly accessing `self.inlines`

This allows subclasses to override `get_inlines()` to dynamically control which inlines are instantiated, exactly as the test expected.

VERDICT: RESOLVED
RE-ENTER: none
