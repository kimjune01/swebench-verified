# Hypothesis graph: django__django-16145

---
## Hypothesis Node: Initial Diagnosis
**Date**: 2026-05-23
**Mode**: Abduction → Deduction
**Confidence**: 95% (deduction - traced code path)

### Failure Summary
Test `test_zero_ip_addr` expects output "Starting development server at http://0.0.0.0:8000/" when running `runserver 0:8000`, but gets "Starting development server at http://0:8000/" instead.

### Root Cause Analysis

The issue is in `django/core/management/commands/runserver.py` at the address normalization logic (lines 88-107).

**Code path**:
1. User provides `addrport="0:8000"`
2. Line 93: Regex `naiveip_re` matches it as `addr="0"` (captured as FQDN group), `port="8000"`
3. Line 100: `if self.addr:` → True (because "0" is not empty)
4. Line 105: `if not self.addr:` → False (because "0" is truthy)
5. **Bug**: self.addr remains "0" instead of being expanded to "0.0.0.0"
6. Line 145: Message printed with `addr=self.addr` which is "0"

**Evidence**:
- `django/core/management/commands/runserver.py:98-107` - Only handles empty addr (`if not self.addr:`), not the special "0" shorthand
- `django/core/management/commands/runserver.py:145` - Outputs self.addr directly without expansion
- Regex test confirms "0:8000" matches as `('0', None, None, '0', '8000')` where addr='0', fqdn='0'

According to Django tutorial documentation, "0" is a shorthand for "0.0.0.0" (bind to all interfaces), but the display message doesn't perform this expansion.

### Edit Sites

**Primary fix**: `django/core/management/commands/runserver.py` lines 105-107
- After the `if not self.addr:` block, add logic to detect `self.addr == "0"` and replace with:
  - "0.0.0.0" for IPv4 (when `not self.use_ipv6`)
  - "::" for IPv6 (when `self.use_ipv6`)

**Specific location**: After line 107, before line 108 (`self.run(**options)`)

### Supporting Evidence
- Socket binding test confirms Python converts "0" → "0.0.0.0" at bind time
- Test file `tests/admin_scripts/tests.py:1601` expects "0.0.0.0" in output
- No existing handling of "0" shorthand found in codebase (grep returned no results for "0.0.0.0" in runserver.py)

### Rejected Hypotheses
None - first diagnosis.

### Open Questions
- Should this also handle IPv6 case "0:8000" with --ipv6 flag? (Test only covers IPv4)

## craft: gate iteration 1

**Drafted fix:**
Added check for `self.addr == "0"` after the empty-string default address logic, mapping "0" to "0.0.0.0" for IPv4 or "::" for IPv6.

**codex review findings:**
- Missing `self._raw_ipv6 = self.use_ipv6` assignment - without it, IPv6 case would format as `http://:::8000/` instead of `http://[::]:8000/`
- Fix should preserve the same invariant as the default-address path

**Applied fix:**
```python
elif self.addr == "0":
    self.addr = "::" if self.use_ipv6 else "0.0.0.0"
    self._raw_ipv6 = self.use_ipv6
```

**Gate result:** ✅ PASS
- All 209 tests passed
- `test_zero_ip_addr` now passes - "0:8000" correctly displays as "http://0.0.0.0:8000/"
- No regressions in existing tests

**Resolution:** The recon diagnosis was correct. The fix expands the "0" shorthand to the proper IP address format for both IPv4 and IPv6, maintaining the internal invariant for bracket formatting.

---
## Audit: django__django-16145
**Date**: 2026-05-23
**Patch verification**: ✅ Live in tree (1 file, 3 insertions)

### Test Results

**Full gate run**: 209 tests in 32.159s - **ALL PASSED**

#### FAIL_TO_PASS
- `test_zero_ip_addr (admin_scripts.tests.ManageRunserver)`: **PASS** ✅

#### PASS_TO_PASS regressions
**None** - All 208 PASS_TO_PASS tests remain passing.

#### Pre-existing failures (not counted)
**None** - Base capture showed only `test_zero_ip_addr` failing, which now passes.

### Patch Analysis

The 3-line fix in `django/core/management/commands/runserver.py`:
```python
elif self.addr == "0":
    self.addr = "::" if self.use_ipv6 else "0.0.0.0"
    self._raw_ipv6 = self.use_ipv6
```

Successfully addresses the root cause identified in recon:
- Catches the "0" shorthand after regex parsing
- Expands to "0.0.0.0" for IPv4 or "::" for IPv6
- Maintains `_raw_ipv6` invariant for proper bracket formatting
- No scope creep - surgical fix for the specific failure mode

### Verification

Gate output confirms target behavior:
- Input `0:8000` now displays as `http://0.0.0.0:8000/` (expected)
- No test failures introduced
- All existing runserver tests pass (addrport, IPv6, hostname, custom defaults, etc.)

VERDICT: RESOLVED
RE-ENTER: none
