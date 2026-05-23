# Hypothesis graph: django__django-15103

---

## Hypothesis Node: H₁ — element_id is required but should be optional

**Type:** Abduction → Deduction (confirmed by code reading)
**Timestamp:** 2026-05-22 (recon phase)

**Observation:**
- `test_without_id` fails: `TemplateSyntaxError: json_script requires 2 arguments, 1 provided`
- `test_json_script_without_id` fails: `TypeError: json_script() missing 1 required positional argument: 'element_id'`

**Hypothesis:**
The `element_id` parameter is currently required in both the core `json_script` function (`django/utils/html.py:64`) and its template filter wrapper (`django/template/defaultfilters.py:86`). Making element_id optional (default to None) and conditionally omitting the id attribute from the output will allow calling json_script with just a value argument.

**Evidence:**
- `django/utils/html.py:64` — `def json_script(value, element_id):` defines element_id as required
- `django/utils/html.py:72-75` — `format_html('<script id="{}" type="application/json">{}</script>', element_id, ...)` always includes id attribute
- `django/template/defaultfilters.py:86` — wrapper also requires element_id
- Test expectations: `<script type="application/json">...</script>` when no id provided

**Confidence:** 99% (deduction — traced from error to code)

**Edit sites:**
1. `django/utils/html.py:64` — Add default: `def json_script(value, element_id=None):`
2. `django/utils/html.py:72-75` — Conditional format_html based on whether element_id is None
3. `django/template/defaultfilters.py:86` — Add default: `def json_script(value, element_id=None):`

**Status:** Active — passed to /craft for implementation

## Craft Implementation (Gate Loop)

### Iteration 1: Draft and Volley

**Drafted patch:**
1. Made `element_id` parameter optional (default=None) in both:
   - `django/utils/html.py:64` - core json_script function
   - `django/template/defaultfilters.py:86` - template filter wrapper
2. Added conditional logic in django/utils/html.py to omit `id` attribute when element_id is None

**Codex review:** No blocking issues. Confirmed patch addresses root cause. Suggested removing unnecessary `else` clause.

**Applied changes:**
- Updated function signatures to `def json_script(value, element_id=None):`
- Modified return logic to conditionally format HTML based on whether element_id is None
- When None: `<script type="application/json">{}</script>`
- When provided: `<script id="{}" type="application/json">{}</script>`

### Iteration 1: Gate Result

**Status:** ✅ PASS

All 19 tests passed, including both FAIL_TO_PASS tests:
- `test_without_id (template_tests.filter_tests.test_json_script.JsonScriptTests)` ✅
- `test_json_script_without_id (utils_tests.test_html.TestUtilsHtml)` ✅

**Resolution:** The fix correctly implements the recon diagnosis. The `element_id` parameter is now optional, and the HTML output conditionally omits the `id` attribute when element_id is None, allowing both template filter and direct function calls to work without providing an element_id.

---

## Audit: django__django-15103

**Timestamp:** 2026-05-22 (verification phase)

### Phase 1: Patch Status
Patch is live in the tree:
- `django/template/defaultfilters.py` — 2 insertions, 1 deletion
- `django/utils/html.py` — 8 insertions, 1 deletion

### Phase 2: Gate Result
All 19 tests passed (0.110s):
- ✅ All FAIL_TO_PASS tests now pass
- ✅ All PASS_TO_PASS tests still pass
- ✅ No regressions

### Phase 3: Classification

#### FAIL_TO_PASS
- `test_without_id (template_tests.filter_tests.test_json_script.JsonScriptTests)`: **PASS** ✅
  - Base: ERROR (TemplateSyntaxError: json_script requires 2 arguments)
  - Now: ok
- `test_json_script_without_id (utils_tests.test_html.TestUtilsHtml)`: **PASS** ✅
  - Base: ERROR (TypeError: missing required positional argument 'element_id')
  - Now: ok

#### PASS_TO_PASS regressions
None. All 17 PASS_TO_PASS tests remain passing.

#### Pre-existing failures (not counted)
None observed in the gate run.

### Phase 4: Verdict
All FAIL_TO_PASS tests pass, zero regressions. The fix successfully makes `element_id` optional and correctly handles the conditional HTML output.

VERDICT: RESOLVED
RE-ENTER: none
