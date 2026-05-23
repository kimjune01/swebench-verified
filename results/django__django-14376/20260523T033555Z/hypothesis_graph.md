# Hypothesis graph: django__django-14376

## H₀: Initial diagnosis (abduction)

**Timestamp**: 2026-05-22 (recon phase)

The tests fail because `django/db/backends/mysql/client.py` line 11 only checks for the deprecated 'db' key in OPTIONS, not the non-deprecated 'database' key.

**Failing tests**:
1. `test_options_non_deprecated_keys_preferred`: When both 'database' and 'db' are in OPTIONS, expects 'database' to be preferred, but line 11 checks 'db' first
2. `test_options_override_settings_proper_values` (keys=('database', 'password')): When OPTIONS has 'database', expects it to override NAME, but line 11 doesn't check for 'database' at all

**Evidence**:
- `client.py:11` - `db = settings_dict['OPTIONS'].get('db', settings_dict['NAME'])`
- `client.py:13-16` - password handling already correct (checks 'password' before 'passwd')

**Classification**: abduction (read the code, pattern-matched to test expectations) - 85% confidence


## Craft Gate Loop

### Iteration 1: Fix Applied

**Edit site**: `django/db/backends/mysql/client.py` line 11

**Change**: Updated database name extraction to check for non-deprecated 'database' key first, then deprecated 'db' key, then fallback to NAME:

```python
# Before:
db = settings_dict['OPTIONS'].get('db', settings_dict['NAME'])

# After:
db = settings_dict['OPTIONS'].get(
    'database',
    settings_dict['OPTIONS'].get('db', settings_dict['NAME'])
)
```

**Codex review**: No functional issues. Fix correctly prefers non-deprecated 'database' over deprecated 'db', preserves backwards compatibility.

**Gate result**: ✅ GREEN - All 9 tests pass
- test_options_non_deprecated_keys_preferred: PASS
- test_options_override_settings_proper_values: PASS  
- test_parameters: PASS

**Status**: RESOLVED

---

## Audit: django__django-14376

**Timestamp**: 2026-05-22 (audit phase)

### Patch Verification
Patch is live: `django/db/backends/mysql/client.py` modified (6 insertions, 1 deletion)

### Gate Results

**FAIL_TO_PASS (all must PASS):**
- test_options_non_deprecated_keys_preferred: ✅ PASS (was FAIL on base)
- test_options_override_settings_proper_values: ✅ PASS (was FAIL on base) 
- test_parameters: ✅ PASS

**PASS_TO_PASS (no regressions allowed):**
- test_basic_params_specified_in_settings: ✅ PASS
- test_can_connect_using_sockets: ✅ PASS
- test_crash_password_does_not_leak: ✅ PASS
- test_fails_with_keyerror_on_incomplete_config: ✅ PASS
- test_options_charset: ✅ PASS
- test_ssl_certificate_is_added: ✅ PASS

**Regressions**: none

**Pre-existing failures (not counted)**: none

### Classification Against Baseline

Baseline showed 2 explicit failures:
1. test_options_non_deprecated_keys_preferred - now fixed ✅
2. test_options_override_settings_proper_values - now fixed ✅

All 9 tests now pass. Gate output:
```
Ran 9 tests in 0.017s
OK
```

### Verdict

All FAIL_TO_PASS tests now pass. Zero PASS_TO_PASS regressions. Fix is effective and safe.

VERDICT: RESOLVED
RE-ENTER: none
