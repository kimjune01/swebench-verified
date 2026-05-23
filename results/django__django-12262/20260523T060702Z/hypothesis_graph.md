# Hypothesis graph: django__django-12262

## H₁: Root cause in parse_bits validation (abduction)

**Observation:** Template tags with keyword-only parameters that have default values incorrectly raise `TemplateSyntaxError: 'tag_name' received unexpected keyword argument 'param'` when the parameter is provided.

**Evidence:**
- Error raised at `django/template/library.py:264-268`
- `unhandled_kwargs` (lines 254-257) only includes keyword-only params WITHOUT defaults
- Validation check (line 264) rejects params not in `unhandled_kwargs`, even if they're valid keyword-only params with defaults

**Root cause:** Line 264 checks `param not in unhandled_kwargs` instead of `param not in kwonly`. Since `unhandled_kwargs` excludes keyword-only parameters with defaults, valid parameters are incorrectly rejected.

**Fix:** Change line 264 from:
```python
if param not in params and param not in unhandled_kwargs and varkw is None:
```
To:
```python
if param not in params and param not in kwonly and varkw is None:
```

This checks if the parameter is valid (in either `params` or `kwonly`), not just if it's required (in `unhandled_kwargs`).

**Confidence:** Deduction — 95%
- Traced code path from error to root cause
- Analyzed variable states at failure point
- Original commit a7c6c705e8 introduced this logic for keyword-only support

**Edit site:**
- `django/template/library.py:264` — change condition to check `kwonly` instead of `unhandled_kwargs`

## Craft gate-loop (iteration 1)

**Applied diff:**
```diff
--- a/django/template/library.py
+++ b/django/template/library.py
@@ -261,7 +261,7 @@ def parse_bits(parser, bits, params, varargs, varkw, defaults,
         if kwarg:
             # The kwarg was successfully extracted
             param, value = kwarg.popitem()
-            if param not in params and param not in unhandled_kwargs and varkw is None:
+            if param not in params and param not in kwonly and varkw is None:
                 # An unexpected keyword argument was supplied
                 raise TemplateSyntaxError(
                     "'%s' received unexpected keyword argument '%s'" %
```

**Gate result:** ✅ ALL PASS (22 tests, 0 failures)

All FAIL_TO_PASS tests now pass:
- test_inclusion_tag_errors (template_tests.test_custom.InclusionTagTests) ... ok
- test_inclusion_tags (template_tests.test_custom.InclusionTagTests) ... ok
- test_simple_tag_errors (template_tests.test_custom.SimpleTagTests) ... ok
- test_simple_tags (template_tests.test_custom.SimpleTagTests) ... ok

**Trajectory:** Immediate convergence - recon diagnosis was correct.

---

# Audit: django__django-12262

## FAIL_TO_PASS
- test_inclusion_tag_errors (template_tests.test_custom.InclusionTagTests): PASS ✅
- test_inclusion_tags (template_tests.test_custom.InclusionTagTests): PASS ✅
- test_simple_tag_errors (template_tests.test_custom.SimpleTagTests): PASS ✅
- test_simple_tags (template_tests.test_custom.SimpleTagTests): PASS ✅

## PASS_TO_PASS regressions
None — all 18 PASS_TO_PASS tests remain passing.

## Pre-existing (not counted, confirmed against base capture)
None — all failures from the base capture are now resolved.

## Verdict analysis

**Patch applied:** 1 file changed (django/template/library.py:264)
- Changed validation check from `param not in unhandled_kwargs` to `param not in kwonly`

**Gate results:** All 22 tests pass
- ✅ All 4 FAIL_TO_PASS tests now pass
- ✅ All 18 PASS_TO_PASS tests remain passing
- ✅ Zero regressions introduced

**Baseline comparison:**
The fail-on-base capture showed 4 tests failing (2 ERRORs + 2 FAILs):
- test_inclusion_tags: ERROR (TemplateSyntaxError for 'inclusion_keyword_only_default')
- test_simple_tags: ERROR (same root cause)
- test_inclusion_tag_errors: FAIL
- test_simple_tag_errors: FAIL

All 4 are now resolved by the fix.

VERDICT: RESOLVED
RE-ENTER: none
