# Hypothesis graph: django__django-13551

## H₀: Email not included in token hash (abduction)

**Observation:** Three test failures all show `self.assertIs(p0.check_token(user, tk1), False)` assertion fails with `AssertionError: True is not False` after changing the user's email address.

**Hypothesis:** The `_make_hash_value` method in `PasswordResetTokenGenerator` does not include the user's email in the hash calculation, so changing the email doesn't invalidate the token.

**Evidence:**
- `django/contrib/auth/tokens.py:102` - The return statement only includes `user.pk + user.password + str(login_timestamp) + str(timestamp)` - no email field
- `django/contrib/auth/tokens.py:79-102` - The docstring mentions password and last_login as invalidation triggers, but not email
- `tests/auth_tests/test_tokens.py:61` - Test expects `check_token` to return `False` after email change, but it returns `True`

**Confidence:** Deduction — 99%
Reading the code directly shows the email is absent from the hash.

**Edit site:**
- `django/contrib/auth/tokens.py` line 102: Add email to the hash value using `getattr(user, user.get_email_field_name(), '')` to safely handle models with custom email field names or no email field.


## Craft gate-loop iteration 1

**Hypothesis**: Email field is missing from `_make_hash_value` hash computation at line 102 of `django/contrib/auth/tokens.py`

**Edit applied**:
- Added email to hash value calculation: `email = getattr(user, user.get_email_field_name(), '') or ''`
- Updated return statement to include email: `return str(user.pk) + user.password + str(login_timestamp) + str(timestamp) + str(email)`
- Updated docstring to document email as item 3 in invalidation factors

**Codex pre-gate review**: Approved with note to update docstring (applied)

**Gate outcome**: GREEN - All 58 tests passed, including both FAIL_TO_PASS tests:
- `test_token_with_different_email` ✓
- `test_token_with_different_secret` ✓

**Trajectory**: Convergent-success (first attempt)


## Audit: django__django-13551

### FAIL_TO_PASS
- test_token_with_different_email (auth_tests.test_tokens.TokenGeneratorTest): **PASS** ✓
- test_token_with_different_secret (auth_tests.test_tokens.TokenGeneratorTest): **PASS** ✓

### PASS_TO_PASS regressions
none

### Pre-existing (not counted, confirmed against base capture)
none

### Gate output
Ran 58 tests in 0.486s - **OK**

All FAIL_TO_PASS tests now pass. Zero regressions in PASS_TO_PASS tests. The fix correctly adds the email field to the token hash value, invalidating tokens when the user's email address changes.

VERDICT: RESOLVED
RE-ENTER: none
