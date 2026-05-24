# Hypothesis graph: django__django-14349

## Hypothesis H₀: Initial diagnosis (abduction)

**Status:** Active
**Type:** Abduction
**Confidence:** 95% (deduction from code trace)

**Observation:**
Tests fail because URLValidator does not raise ValidationError for URLs containing newline (\n), carriage return (\r), or tab (\t) characters. Eight test cases fail with "AssertionError: ValidationError not raised".

**Root cause:**
URLValidator uses `urlsplit()` from urllib.parse (line 116) to handle IDN domains. Python versions with bpo-43882 fix strip \n, \r, and \t characters before parsing URLs. 

The code flow:
1. URLValidator.__call__ receives URL with forbidden characters
2. `super().__call__(value)` runs regex validation (line 110)
3. Regex correctly rejects (has `[^\s]*` pattern matching no whitespace)
4. ValidationError is caught (line 111)
5. IDN handling code calls `urlsplit(value)` (line 116)
6. **BUG**: urlsplit strips \n, \r, \t characters
7. Reconstructed URL via `urlunsplit` (line 123) no longer has forbidden characters
8. `super().__call__(url)` passes validation with sanitized URL
9. No ValidationError raised

**Evidence:**
- django/core/validators.py:116 - `scheme, netloc, path, query, fragment = urlsplit(value)`
- django/core/validators.py:123 - `url = urlunsplit((scheme, netloc, path, query, fragment))`
- Confirmed urlsplit behavior: `urlsplit('http://example.com/\n').geturl()` returns `'http://example.com/'` (newline stripped)

**Fix:**
Add explicit check for \n, \r, \t characters in URLValidator.__call__ before any urlsplit processing, similar to ProhibitNullCharactersValidator pattern (line 541-556).

**Edit sites:**
- django/core/validators.py:100-145 (URLValidator.__call__ method)
  - Add check after scheme validation (line 107) but before regex check (line 110)
  - Reject if value contains '\n', '\r', or '\t'

## Gate iteration 1

**Hypothesis**: Add check for \n, \r, \t characters in URLValidator.__call__ before urlsplit() can strip them.

**Implementation**: Added early rejection check after scheme validation (line 107) that raises ValidationError if value contains any of '\n', '\r', or '\t'.

**Gate result**: ✅ PASS - all 19 tests pass, including test_validators

**Evidence**: FAIL_TO_PASS test now passes:
- test_validators (validators.tests.TestValidators) ... ok

The fix correctly rejects URLs containing newline, carriage return, or tab characters before Python's urlsplit() can strip them, preventing the false validation pass in the IDN handling path.

---

# Audit: django__django-14349

## FAIL_TO_PASS
- test_validators (validators.tests.TestValidators): PASS ✓

## PASS_TO_PASS regressions
None

## Pre-existing (not counted, confirmed against base capture)
None

## Summary
Patch successfully resolved the issue. URLValidator now rejects URLs containing newline, carriage return, or tab characters before urlsplit() can strip them. All FAIL_TO_PASS tests pass, all PASS_TO_PASS tests remain passing, zero regressions.

VERDICT: RESOLVED
RE-ENTER: none
