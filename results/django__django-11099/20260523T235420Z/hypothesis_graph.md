# Hypothesis graph: django__django-11099

## H₀: Initial failure observation (abduction)
**Timestamp:** 2026-05-23
**Status:** Confirmed
**Confidence:** 95% (induction - test run confirmed)

The tests `test_ascii_validator` and `test_unicode_validator` fail because ValidationError is not raised when usernames contain trailing newlines (e.g., `'trailingnewline\n'`).

**Evidence:**
- `tests/auth_tests/test_validators.py:261` - test_ascii_validator expects ValidationError for `'trailingnewline\n'` but none is raised
- `tests/auth_tests/test_validators.py:249` - test_unicode_validator expects ValidationError for `'trailingnewline
'` but none is raised

## H₁: Root cause - regex $ anchor matches before trailing newline (deduction)
**Timestamp:** 2026-05-23
**Status:** Confirmed
**Confidence:** 99% (deduction - traced and experimentally verified)

Both `ASCIIUsernameValidator` and `UnicodeUsernameValidator` use the regex pattern `r'^[\w.@+-]+$'`. In Python regex, the `$` anchor matches both at the end of the string AND before a trailing newline character. This is a well-documented quirk of Python's regex engine.

**Evidence:**
- `django/contrib/auth/validators.py:10` - ASCIIUsernameValidator uses `regex = r'^[\w.@+-]+$'`
- `django/contrib/auth/validators.py:20` - UnicodeUsernameValidator uses `regex = r'^[\w.@+-]+$'`
- Experimental verification: `re.match(r'^[\w.@+-]+$', 'test\n')` returns a match (True)
- Experimental verification: `re.match(r'\A[\w.@+-]+\Z', 'test\n')` returns no match (False)

**Fix:**
Replace `^` and `$` anchors with `\A` and `\Z` respectively. `\A` matches only at the start of the string, and `\Z` matches only at the end of the string (not before a trailing newline).


## Gate Loop — Iteration 1

**Patch applied:**
Changed regex anchors from `^...$` to `\A...\Z` in both `ASCIIUsernameValidator` and `UnicodeUsernameValidator` in `django/contrib/auth/validators.py`.

**Codex pre-gate review:**
- Confirmed `\A...\Z` is the correct fix for rejecting trailing newlines
- No blocking issues identified
- Expected behavior: stricter validation (intentional)

**Gate result:** ✅ PASS

All 22 tests pass, including the 3 FAIL_TO_PASS tests:
- `test_ascii_validator` (auth_tests.test_validators.UsernameValidatorsTests)
- `test_unicode_validator` (auth_tests.test_validators.UsernameValidatorsTests)
- `test_help_text` (auth_tests.test_validators.UserAttributeSimilarityValidatorTest)

**Trajectory:** Convergent (immediate resolution)

**Resolution:** Complete. The recon diagnosis was accurate — Python's `$` anchor matches before trailing newlines, and switching to `\Z` correctly rejects usernames with trailing newlines while preserving all valid username patterns.

---

# Audit: django__django-11099

## FAIL_TO_PASS
- test_ascii_validator (auth_tests.test_validators.UsernameValidatorsTests): PASS ✓
- test_unicode_validator (auth_tests.test_validators.UsernameValidatorsTests): PASS ✓
- test_help_text (auth_tests.test_validators.UserAttributeSimilarityValidatorTest): PASS ✓

## PASS_TO_PASS regressions
none

## Pre-existing (not counted, confirmed against base capture)
none

## Summary
The craft patch successfully resolved the issue by replacing `^` and `$` anchors with `\A` and `\Z` in both ASCIIUsernameValidator and UnicodeUsernameValidator regex patterns. This prevents usernames with trailing newlines from passing validation, as `^` and `$` match at line boundaries while `\A` and `\Z` only match at string start/end.

All 22 tests pass. The two previously failing tests (test_ascii_validator and test_unicode_validator) now correctly raise ValidationError for usernames with trailing newlines.

VERDICT: RESOLVED
RE-ENTER: none
