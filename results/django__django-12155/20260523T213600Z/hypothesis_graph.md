# Hypothesis graph: django__django-12155

## Node 1: Initial Hypothesis (Abduction)
**Timestamp:** 2026-05-23 (recon phase 1)
**Status:** CONFIRMED

### H₀: Test failure due to incorrect indentation calculation
The test `test_parse_rst_with_docstring_no_leading_line_feed` fails because `trim_docstring()` incorrectly calculates indentation by including the first line, resulting in `indent=0` for docstrings that start with text on the first line (e.g., `"firstline\n\n    second line"`). This leaves the body with leading spaces (`"    second line"`), which causes docutils to produce a system-message error instead of clean HTML.

**Evidence:**
- Test expects: `parse_rst(body, '')` returns `'<p>second line</p>\n'` with no stderr
- Test gets: System message div in output, indicating docutils parsing error
- `django/contrib/admindocs/utils.py:37` - Current code: `indent = min(len(line) - len(line.lstrip()) for line in lines if line.lstrip())`
- For input `"firstline\n\n    second line"`, this calculates: `min(0, 4) = 0`
- Result: body is `"    second line"` (still indented) instead of `"second line"`

**Reasoning mode:** Deduction (traced code execution, verified with simulation)
**Confidence:** 99%

### Root Cause
`trim_docstring()` at line 37 includes the first line when calculating minimum indentation, violating PEP 257's specification that "the first line should be used only for a one-line summary" and "any further indentation should be determined by the second and subsequent lines."

### Edit Site
**File:** `django/contrib/admindocs/utils.py`
**Line:** 37
**Change:** Skip the first line when calculating indent, and handle edge cases where there are no non-empty lines after the first line.

From:
```python
indent = min(len(line) - len(line.lstrip()) for line in lines if line.lstrip())
```

To:
```python
indent = min((len(line) - len(line.lstrip()) for line in lines[1:] if line.lstrip()), default=0)
```

**Rationale:** 
- `lines[1:]` skips the first line per PEP 257
- `default=0` handles edge cases (single-line docstrings, no content after first line)
- Parentheses around generator expression required when using `default` parameter


## Gate Loop - Iteration 1

**Drafted Fix:**
Changed `django/contrib/admindocs/utils.py:37` from:
```python
indent = min(len(line) - len(line.lstrip()) for line in lines if line.lstrip())
```
to:
```python
indent = min([len(line) - len(line.lstrip()) for line in lines[1:] if line.lstrip()] or [0])
```

**Codex Feedback:**
- Core fix is correct per PEP 257
- Python compatibility concern: used `[...] or [0]` form instead of `min(..., default=0)`

**Gate Result:** ✅ GREEN
All 7 tests passed, including `test_parse_rst_with_docstring_no_leading_line_feed`.

**Status:** RESOLVED

---

# Audit: django__django-12155

## FAIL_TO_PASS
- test_parse_rst_with_docstring_no_leading_line_feed: PASS ✓

## PASS_TO_PASS regressions
none

## Pre-existing (not counted, confirmed against base capture)
none

## Patch
```diff
diff --git a/django/contrib/admindocs/utils.py b/django/contrib/admindocs/utils.py
index 4c0e7e2a56..ff06f070f0 100644
--- a/django/contrib/admindocs/utils.py
+++ b/django/contrib/admindocs/utils.py
@@ -34,7 +34,7 @@ def trim_docstring(docstring):
         return ''
     # Convert tabs to spaces and split into lines
     lines = docstring.expandtabs().splitlines()
-    indent = min(len(line) - len(line.lstrip()) for line in lines if line.lstrip())
+    indent = min([len(line) - len(line.lstrip()) for line in lines[1:] if line.lstrip()] or [0])
     trimmed = [lines[0].lstrip()] + [line[indent:].rstrip() for line in lines[1:]]
     return "\n".join(trimmed).strip()
```

## Summary
The fix correctly handles docstrings where the first line has no leading whitespace by excluding `lines[0]` from the indent calculation and providing a fallback of `[0]` when all remaining lines are empty/whitespace-only. All 7 tests pass with zero regressions.

VERDICT: RESOLVED
RE-ENTER: none
