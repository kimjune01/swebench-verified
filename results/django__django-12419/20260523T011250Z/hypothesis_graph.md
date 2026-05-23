# Hypothesis graph: django__django-12419

## H0: Test fails because SECURE_REFERRER_POLICY default is None [ABDUCTION]

**Observation:** Test `test_middleware_headers` expects `b'Referrer-Policy: same-origin'` in HTTP headers but it's missing.

**Trace:**
- Test loads default MIDDLEWARE from project template (includes SecurityMiddleware)
- Test checks that response headers include `Referrer-Policy: same-origin`
- SecurityMiddleware.process_response() only adds Referrer-Policy header if `self.referrer_policy` is truthy (line 46)
- `self.referrer_policy` is set from `settings.SECURE_REFERRER_POLICY` (line 18)
- Default in `django/conf/global_settings.py:640` is `SECURE_REFERRER_POLICY = None`
- None is falsy, so no header is added

**Evidence:**
- `django/conf/global_settings.py:640`: `SECURE_REFERRER_POLICY = None`
- `django/middleware/security.py:18`: `self.referrer_policy = settings.SECURE_REFERRER_POLICY`
- `django/middleware/security.py:46`: `if self.referrer_policy:` (only adds header if truthy)

**Root cause:** The default value for SECURE_REFERRER_POLICY is None, causing no header to be sent.

**Fix:** Change default from `None` to `'same-origin'` in global_settings.py

**Confidence:** Deduction - 99%

---

## Craft gate loop (iteration 1)

**Edit applied:**
- `django/conf/global_settings.py:640`: Changed `SECURE_REFERRER_POLICY = None` to `SECURE_REFERRER_POLICY = 'same-origin'`

**codex pre-gate review:** Mechanically correct. Noted potential docs/release notes needed, but fix itself is sound.

**Gate result:** ✅ PASS
```
test_middleware_headers (project_template.test_settings.TestStartProjectSettings) ... ok
Ran 1 test in 0.003s
OK
```

**Trajectory:** Convergent-success on first attempt. Recon diagnosis was correct — the default value change was sufficient.

**Resolution:** FAIL_TO_PASS test passes. No regressions detected by gate.

---

# Audit: django__django-12419

## FAIL_TO_PASS
- test_middleware_headers (project_template.test_settings.TestStartProjectSettings): **PASS**

## PASS_TO_PASS regressions
None (PASS_TO_PASS list was empty)

## Pre-existing (not counted, confirmed against base capture)
None

## Patch applied
```diff
diff --git a/django/conf/global_settings.py b/django/conf/global_settings.py
index 09c9b95d26..8bb59a4037 100644
--- a/django/conf/global_settings.py
+++ b/django/conf/global_settings.py
@@ -637,6 +637,6 @@ SECURE_HSTS_INCLUDE_SUBDOMAINS = False
 SECURE_HSTS_PRELOAD = False
 SECURE_HSTS_SECONDS = 0
 SECURE_REDIRECT_EXEMPT = []
-SECURE_REFERRER_POLICY = None
+SECURE_REFERRER_POLICY = 'same-origin'
 SECURE_SSL_HOST = None
 SECURE_SSL_REDIRECT = False
```

## Gate output
```
test_middleware_headers (project_template.test_settings.TestStartProjectSettings) ... ok

----------------------------------------------------------------------
Ran 1 test in 0.003s

OK
```

## Analysis
The fix changes the default value of `SECURE_REFERRER_POLICY` from `None` to `'same-origin'` in Django's global settings. This causes the `SecurityMiddleware` to emit the `Referrer-Policy: same-origin` header by default, which is what the test expects.

The baseline failure showed the test was expecting `Referrer-Policy: same-origin` but the header was missing. The craft patch successfully adds this header by setting the default value.

VERDICT: RESOLVED
RE-ENTER: none
