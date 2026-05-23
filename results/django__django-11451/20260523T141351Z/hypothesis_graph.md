# Hypothesis graph: django__django-11451

## H₀: Initial diagnosis (abduction, confidence: 98%)

**Observation:** The `test_authentication_without_credentials` test fails with "1 queries executed, 0 expected" when `ModelBackend.authenticate()` is called with incomplete credentials (missing username, password, or both).

**Root cause:** `ModelBackend.authenticate()` in `django/contrib/auth/backends.py:39-50` does not check if username or password is None before attempting database query via `get_by_natural_key(username)` at line 43. This causes pointless queries like `WHERE username IS NULL`.

**Supporting evidence:**
- Lines 40-41: username can remain None after extraction from kwargs
- Line 43: Database query happens regardless of username value
- Lines 44-47: Expensive password hasher runs even on DoesNotExist
- Test file line 239: Expects 0 queries for incomplete credentials
- Problem description: "username isn't a nullable field" confirms NULL queries are pointless

**Proposed fix:** Add early return `if username is None or password is None: return` after line 41, before the database query at line 43.

**Reasoning:** Authentication requires both username AND password. If either is missing, authentication cannot succeed, so the method should return None immediately. The timing attack mitigation (#20760) is for masking existing vs non-existing users, not for masking differences between different authentication backends.

## Gate Loop - Iteration 1

**Applied fix:** Added early return check in `ModelBackend.authenticate()` at `django/contrib/auth/backends.py` lines 42-43:
```python
if username is None or password is None:
    return
```

**Rationale:** Prevent database queries and password hasher execution when credentials are incomplete (missing username or password).

**Gate result:** ✅ GREEN - All 57 tests passed, including all 6 FAIL_TO_PASS tests:
- `test_authentication_without_credentials` (ModelBackendTest)
- `test_custom_perms` (ModelBackendTest)
- `test_authentication_without_credentials` (CustomPermissionsUserModelBackendTest)
- `test_custom_perms` (CustomPermissionsUserModelBackendTest)
- `test_authentication_without_credentials` (ExtensionUserModelBackendTest)
- `test_custom_perms` (ExtensionUserModelBackendTest)

**Status:** RESOLVED - Fix successfully applied in single iteration.

---

# Audit: django__django-11451

## FAIL_TO_PASS
- test_authentication_without_credentials (auth_tests.test_auth_backends.ModelBackendTest): **PASS** ✓
- test_custom_perms (auth_tests.test_auth_backends.ModelBackendTest): **PASS** ✓
- test_authentication_without_credentials (auth_tests.test_auth_backends.CustomPermissionsUserModelBackendTest): **PASS** ✓
- test_custom_perms (auth_tests.test_auth_backends.CustomPermissionsUserModelBackendTest): **PASS** ✓
- test_authentication_without_credentials (auth_tests.test_auth_backends.ExtensionUserModelBackendTest): **PASS** ✓
- test_custom_perms (auth_tests.test_auth_backends.ExtensionUserModelBackendTest): **PASS** ✓

## PASS_TO_PASS regressions
None - all 57 tests passed.

## Pre-existing (not counted, confirmed against base capture)
None - no pre-existing failures affected the audit.

## Patch verification
```diff
diff --git a/django/contrib/auth/backends.py b/django/contrib/auth/backends.py
@@ -39,6 +39,8 @@ class ModelBackend(BaseBackend):
     def authenticate(self, request, username=None, password=None, **kwargs):
         if username is None:
             username = kwargs.get(UserModel.USERNAME_FIELD)
+        if username is None or password is None:
+            return
         try:
             user = UserModel._default_manager.get_by_natural_key(username)
```

The patch adds an early return when username or password is None, preventing unnecessary database queries and password hasher execution when credentials are incomplete. This resolves the test failures that expected 0 database queries when authenticating without credentials.

All 6 FAIL_TO_PASS tests now pass, and no PASS_TO_PASS tests regressed. The fix is minimal, targeted, and correct.
