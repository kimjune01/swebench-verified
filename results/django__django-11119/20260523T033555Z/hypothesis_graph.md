# Hypothesis graph: django__django-11119

---

## Hypothesis Node: Initial Diagnosis
**Status**: Active  
**Type**: Abduction → Deduction (traced through code)  
**Timestamp**: 2026-05-22

### Observation
Test `test_autoescape_off` fails with:
- Expected: `'obj:<script>\n'` (unescaped)
- Got: `'obj:&lt;script&gt;\n'` (HTML-escaped)

Engine created with `autoescape=False` but output is still autoescaped.

### Root Cause Hypothesis
`Engine.render_to_string()` at line 163 of `django/template/engine.py` creates a `Context` object without passing the engine's `self.autoescape` attribute. Since `Context.__init__` defaults `autoescape=True`, the context always autoescapes regardless of the engine's setting.

### Evidence Trail
1. `django/template/engine.py:163` — `return t.render(Context(context))` 
   - Creates Context without autoescape parameter
2. `django/template/context.py:137` — `def __init__(self, dict_=None, autoescape=True, ...)`
   - Context defaults to autoescape=True
3. `django/template/engine.py:44` — `self.autoescape = autoescape`
   - Engine stores its autoescape setting but doesn't use it when creating Context
4. Git history shows commit 19a5f6da32 added autoescape to Engine but didn't update render_to_string

### Proposed Fix
Change line 163 from:
```python
return t.render(Context(context))
```
to:
```python
return t.render(Context(context, autoescape=self.autoescape))
```

### Confidence
**99% (Deduction)** — Direct code trace shows the missing parameter. No other plausible explanation.

### Edit Sites
- `django/template/engine.py:163` — Add `autoescape=self.autoescape` parameter to Context constructor


## /craft gate loop

### Iteration 1: Draft + Volley + Apply

**Drafted fix:** Modified `django/template/engine.py` line 163 to pass `autoescape=self.autoescape` when creating a new `Context` in `render_to_string()`:

```diff
--- a/django/template/engine.py
+++ b/django/template/engine.py
@@ -163,7 +163,7 @@ class Engine:
-            return t.render(Context(context))
+            return t.render(Context(context, autoescape=self.autoescape))
```

**Codex volley:** Approved. Confirmed the fix is correct, low risk, and only affects the non-Context path. Noted that existing Context instances are correctly left untouched.

**Gate result:** ✅ **GREEN** — all 8 tests pass, including `test_autoescape_off`.

**Classification:** Convergent success on first iteration.

**Resolution:** FAIL_TO_PASS test now passes. The fix correctly propagates the engine's `autoescape` setting to the Context when rendering with a plain dict, solving the reported bug where `autoescape=False` was being ignored in `render_to_string()`.

---

## /audit Final Verification

**Timestamp**: 2026-05-22  
**Patch applied**: Yes (1 file, 1 insertion, 1 deletion)

### Patch Content
```diff
diff --git a/django/template/engine.py b/django/template/engine.py
index dfaa67ba12..ff9ce58d59 100644
--- a/django/template/engine.py
+++ b/django/template/engine.py
@@ -160,7 +160,7 @@ class Engine:
         if isinstance(context, Context):
             return t.render(context)
         else:
-            return t.render(Context(context))
+            return t.render(Context(context, autoescape=self.autoescape))
```

### Gate Results

**Full test suite**: 8 tests, all PASS

### FAIL_TO_PASS
- `test_autoescape_off (template_tests.test_engine.RenderToStringTest)`: ✅ **PASS**

### PASS_TO_PASS (no regressions)
- `test_cached_loader_priority (template_tests.test_engine.LoaderTests)`: ✅ **PASS**
- `test_loader_priority (template_tests.test_engine.LoaderTests)`: ✅ **PASS**
- `test_origin (template_tests.test_engine.LoaderTests)`: ✅ **PASS**
- `test_basic_context (template_tests.test_engine.RenderToStringTest)`: ✅ **PASS**
- `test_multiple_engines_configured (template_tests.test_engine.GetDefaultTests)`: ✅ **PASS**
- `test_no_engines_configured (template_tests.test_engine.GetDefaultTests)`: ✅ **PASS**
- `test_single_engine_configured (template_tests.test_engine.GetDefaultTests)`: ✅ **PASS**

### Pre-existing failures
None (test_autoescape_off was pre-existing on base, now resolved)

### Kill report
N/A — patch is RESOLVED

VERDICT: RESOLVED
RE-ENTER: none
