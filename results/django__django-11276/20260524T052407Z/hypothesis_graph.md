# Hypothesis graph: django__django-11276

## H1: Initial diagnosis - escape() uses custom dictionary instead of stdlib
**Type**: Abduction → Deduction (99% confidence)
**Timestamp**: Phase 1 recon

### Observation
Tests expect single quotes escaped as `&#x27;` but get `&#39;`:
- `tests/utils_tests/test_html.py`: AssertionError: '&#39;' != '&#x27;'
- `tests/template_tests/filter_tests/test_make_list.py`: AssertionError: '[&#39;&amp;&#39;]' != '[&#x27;&amp;&#x27;]'
- 28 failures, 1 error across multiple test modules

### Root cause
`django/utils/html.py` escape() function uses custom `_html_escapes` dictionary:
```python
_html_escapes = {
    ord('&'): '&amp;',
    ord('<'): '&lt;',
    ord('>'): '&gt;',
    ord('"'): '&quot;',
    ord("'"): '&#39;',  # <-- Should be &#x27; per stdlib
}

@keep_lazy(str, SafeString)
def escape(text):
    return mark_safe(str(text).translate(_html_escapes))
```

Python stdlib `html.escape()` uses `&#x27;` (hex entity) instead of `&#39;` (decimal entity).
Tests updated to expect stdlib behavior, but implementation not changed yet.

### Evidence
- `django/utils/html.py:32` — `ord("'"): '&#39;'`
- `django/utils/html.py:46` — Uses `.translate(_html_escapes)`
- `django/utils/html.py:269` — `unescape()` helper converts `&#39;` back: `.replace('&#39;', "'")`
- Verified `html.escape(chr(39))` returns `'&#x27;'` in Python 3.6+
- `_html_escapes` only used in 2 places (definition and escape function)

### Edit sites required
1. **Import** (line ~7): Add `from html import escape as html_escape`
2. **Remove** (lines 27-33): Delete `_html_escapes` dictionary (no longer needed)
3. **Modify** (lines 38-46): Change `escape()` to use `html_escape()`:
   ```python
   @keep_lazy(str, SafeString)
   def escape(text):
       return mark_safe(html_escape(str(text)))
   ```
4. **Modify** (line 269): Update `unescape()` in `urlize()`:
   - Change `.replace('&#39;', "'")` to `.replace('&#x27;', "'")`

### Confidence: Deduction — 99%
Call path traced, stdlib behavior verified, no competing hypotheses.

## Craft Gate Loop - Iteration 1

**Changes applied:**
1. Added import: `from html import escape as html_escape`
2. Removed `_html_escapes` dictionary entirely
3. Updated `escape()` function to use `html_escape(str(text))` instead of `.translate(_html_escapes)`
4. Updated `unescape()` helper in `urlize()` to support BOTH `&#39;` and `&#x27;` for backward compatibility

**Codex feedback incorporated:**
- Modified unescape to handle both decimal (`&#39;`) and hexadecimal (`&#x27;`) single quote entities for backward compatibility with existing HTML

**Gate result:**
- 580 tests ran, 579 passed
- 1 error: UnicodeDecodeError in `test_strip_tags_files` (pre-existing environmental issue, unrelated to our changes)
- All FAIL_TO_PASS tests verified passing:
  - test_addslashes02 ✅
  - test_title1 ✅
  - test_urlize01 ✅
  - test_make_list02 ✅
  - test_password_help_text ✅
  - test_url_split_chars ✅
  - test_wrapping_characters ✅

**Status:** RESOLVED - All FAIL_TO_PASS tests pass

---

# Audit: django__django-11276

## FAIL_TO_PASS
- test_make_list02 (template_tests.filter_tests.test_make_list.MakeListTests): **PASS** ✓
- test_password_help_text (auth_tests.test_forms.UserCreationFormTest): **PASS** ✓
- test_url_split_chars (template_tests.filter_tests.test_urlize.FunctionTests): **PASS** ✓
- test_wrapping_characters (template_tests.filter_tests.test_urlize.FunctionTests): **PASS** ✓
- test_addslashes02 (template_tests.filter_tests.test_addslashes.AddslashesTests): **PASS** ✓
- test_title1 (template_tests.filter_tests.test_title.TitleTests): **PASS** ✓
- test_urlize01 (template_tests.filter_tests.test_urlize.UrlizeTests): **PASS** ✓
- test_urlize06 (template_tests.filter_tests.test_urlize.UrlizeTests): **PASS** ✓

## PASS_TO_PASS regressions
None. Gate shows 0 failures (baseline had 28 failures + 1 error, now 0 failures + 1 error).

## Pre-existing (not counted, confirmed against base capture)
- test_strip_tags_files (utils_tests.test_html.TestUtilsHtml): UnicodeDecodeError: 'ascii' codec can't decode byte 0xc2 in position 257 (existed in baseline as "errors=1")

## Patch summary
```diff
diff --git a/django/utils/html.py b/django/utils/html.py
@@ -2,6 +2,7 @@
+from html import escape as html_escape
@@ -24,14 +25,6 @@
-_html_escapes = {
-    ord('&'): '&amp;',
-    ord('<'): '&lt;',
-    ord('>'): '&gt;',
-    ord('"'): '&quot;',
-    ord("'"): '&#39;',
-}
-
@@ -43,7 +36,7 @@ def escape(text):
-    return mark_safe(str(text).translate(_html_escapes))
+    return mark_safe(html_escape(str(text)))
@@ -266,7 +259,7 @@ def urlize(text, trim_url_limit=None, nofollow=False, autoescape=False):
         return text.replace('&amp;', '&').replace('&lt;', '<').replace(
-            '&gt;', '>').replace('&quot;', '"').replace('&#39;', "'")
+            '&gt;', '>').replace('&quot;', '"').replace('&#39;', "'").replace('&#x27;', "'")
```

**Key changes:**
1. Replaced custom `_html_escapes` dictionary with stdlib `html.escape()`
2. Stdlib uses `&#x27;` (hexadecimal) for single quotes vs Django's old `&#39;` (decimal)
3. Added `&#x27;` handling to `unescape()` helper for backward compatibility

VERDICT: RESOLVED
RE-ENTER: none
