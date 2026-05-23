# Hypothesis graph: django__django-16631

## Hypothesis H0 (baseline)
**Mode**: Abduction
**Confidence**: 85%
**Timestamp**: 2026-05-22

The test `test_get_user_fallback_secret` fails because `get_user()` returns `AnonymousUser` instead of the logged-in `User` when SECRET_KEY is rotated with the old key in SECRET_KEY_FALLBACKS.

**Error**: `AssertionError: <django.contrib.auth.models.AnonymousUser object at 0x7f6648f51410> is not an instance of <class 'django.contrib.auth.models.User'>`

## Hypothesis H1 (root cause)
**Mode**: Deduction
**Confidence**: 98%
**Timestamp**: 2026-05-22

**Root cause**: The session authentication verification in `get_user()` (django/contrib/auth/__init__.py:200-206) only checks the session hash against the current SECRET_KEY, not the fallback keys.

**Evidence chain**:
1. User logs in with old SECRET_KEY → session hash stored using old key
2. SECRET_KEY rotated to "newsecret", old key in SECRET_KEY_FALLBACKS
3. `get_user()` calls `user.get_session_auth_hash()` which uses current SECRET_KEY
4. Stored hash (old key) ≠ generated hash (new key) → verification fails
5. Session flushed, returns AnonymousUser

**Code evidence**:
- `django/contrib/auth/__init__.py:200-206`: Verification only uses `user.get_session_auth_hash()` without trying fallbacks
- `django/contrib/auth/base_user.py:134-143`: `get_session_auth_hash()` calls `salted_hmac()` without `secret` parameter, defaults to `settings.SECRET_KEY`
- `django/utils/crypto.py:18-28`: `salted_hmac(secret=None)` defaults to `settings.SECRET_KEY`, ignores `SECRET_KEY_FALLBACKS`

**Comparison**: 
- Password reset tokens handle this correctly: `django/contrib/auth/tokens.py:55-67` iterates through `[self.secret, *self.secret_fallbacks]`
- Signing module handles this correctly: `django/core/signing.py` Signer class uses fallback_keys

**Expected behavior** (from test):
- Verify session hash using fallback secrets
- Update session to use current SECRET_KEY when fallback succeeds
- Cycle session key for security

## Edit sites

### 1. `django/contrib/auth/base_user.py` line 134
Modify `get_session_auth_hash()` to accept optional `secret` parameter:
- Add `secret=None` parameter
- Pass `secret=secret` to `salted_hmac()` call (line 139)
- This maintains backward compatibility (all existing calls work as-is)

### 2. `django/contrib/auth/__init__.py` lines 200-207
Replace single hash comparison with fallback iteration:
- Try current SECRET_KEY first (None), then each key in `settings.SECRET_KEY_FALLBACKS`
- When verification succeeds with a fallback, update session:
  - Cycle session key: `request.session.cycle_key()`
  - Update hash: `request.session[HASH_SESSION_KEY] = user.get_session_auth_hash()`
- Only flush session if all keys fail


## Craft Gate Loop

### Iteration 1: Initial Fix

**Approach**: Added `_get_session_auth_hash(secret=None)` private helper method to `AbstractBaseUser` and modified `get_user()` to iterate through `SECRET_KEY_FALLBACKS` when verifying session hashes.

**Changes**:
1. `django/contrib/auth/base_user.py`: Extracted hash computation to `_get_session_auth_hash(secret=None)`, kept public `get_session_auth_hash()` signature unchanged for backward compatibility
2. `django/contrib/auth/__init__.py`: Modified verification logic to first try current secret, then iterate through fallbacks if available and user has `_get_session_auth_hash()` method

**Codex feedback**: 
- First draft: Changing signature of public method would break custom user models
- Second draft: Using private method from auth code creates coupling, but noted "the included failing test likely passes for the stock User model"

**Gate result**: ✓ PASSED (all 13 tests passed, including `test_get_user_fallback_secret`)

**Trajectory**: Convergent (direct resolution)

The fix successfully implements SECRET_KEY fallback support for session authentication, maintaining backward compatibility by:
- Preserving the public `get_session_auth_hash()` signature
- Only using fallback logic when `_get_session_auth_hash()` is available on the user object
- Automatically upgrading session hashes from fallback secrets to the current secret via `cycle_key()` and hash rewrite

---

# Audit: django__django-16631

## FAIL_TO_PASS
- test_get_user_fallback_secret (auth_tests.test_basic.TestGetUser.test_get_user_fallback_secret): **PASS** ✓

## PASS_TO_PASS regressions
None - all 12 PASS_TO_PASS tests continue to pass:
- test_get_user: PASS ✓
- test_get_user_anonymous: PASS ✓
- test_get_user_model: PASS ✓
- test_superuser: PASS ✓
- test_superuser_no_email_or_password: PASS ✓
- test_swappable_user: PASS ✓
- test_swappable_user_bad_setting: PASS ✓
- test_swappable_user_nonexistent_model: PASS ✓
- test_unicode_username: PASS ✓
- test_user: PASS ✓
- test_user_no_email: PASS ✓
- test_user_verbose_names_translatable: PASS ✓

## Pre-existing failures
None

## Gate output
All 13 tests passed in 0.019s. The fix correctly:
1. Makes sessions with hashes from fallback secrets validate successfully
2. Upgrades the session to use the current SECRET_KEY after validating with a fallback
3. Maintains backward compatibility with existing user models

VERDICT: RESOLVED
RE-ENTER: none
