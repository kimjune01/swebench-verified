# Hypothesis graph: sympy__sympy-20916

## H₀: ASCII-only regex pattern fails to match Unicode characters (ACTIVE)
**Type:** Abduction → Deduction (confirmed by code inspection and testing)
**Confidence:** 98%
**Status:** Active hypothesis for craft

### Observation
The `split_super_sub` function fails to extract trailing digits as subscripts when:
1. The base name contains Greek letters (e.g., `ω`)
2. The trailing subscript contains Unicode digits (e.g., `𝟙`)

Test cases failing:
- `split_super_sub("ω1")` returns `('ω1', [], [])` instead of `('ω', [], ['1'])`
- `split_super_sub("w𝟙")` returns `('w𝟙', [], [])` instead of `('w', [], ['𝟙'])`

### Root cause
File: `sympy/printing/conventions.py`
Line 10: `_name_with_digits_p = re.compile(r'^([a-zA-Z]+)([0-9]+)$')`
Lines 65-68: Regex application

The regex pattern `r'^([a-zA-Z]+)([0-9]+)$'` restricts matching to:
- First group: ASCII letters only `[a-zA-Z]`
- Second group: ASCII digits only `[0-9]`

This fails for:
- Greek letters like ω (U+03C9), α (U+03B1), etc.
- Unicode mathematical digits like 𝟙 (U+1D7D9)

### Evidence trail
1. Read `sympy/printing/conventions.py` — found regex pattern on line 10
2. Traced code flow: lines 36-57 parse delimiters, line 65 applies regex to extract trailing digits
3. Tested current behavior: confirmed Unicode characters not matched
4. Verified Python built-ins: `'ω'.isalpha() == True`, `'𝟙'.isdigit() == True`
5. Git history: no recent changes to this pattern, longstanding limitation

### Proposed fix
Replace regex-based matching (lines 10, 65-68) with Unicode-aware string methods:
```python
# Instead of regex match at lines 65-68:
i = len(name)
while i > 0 and name[i-1].isdigit():
    i -= 1
if 0 < i < len(name) and all(c.isalpha() for c in name[:i]):
    base_name = name[:i]
    sub = name[i:]
    name = base_name
    subs.insert(0, sub)
```

This uses `str.isdigit()` and `str.isalpha()` which are Unicode-aware by default in Python 3.

### Killability
This hypothesis is killed if:
- The fix causes any existing test to fail (regression)
- The Unicode test cases still fail after the fix
- The fix doesn't handle all Unicode digit/letter combinations


## Craft Gate Loop

### Iteration 1: Initial fix with isdecimal()

**Change applied:**
- Removed `import re` (line 5)
- Removed `_name_with_digits_p` regex pattern (line 10)
- Replaced regex matching logic (lines 65-68) with Unicode-aware string parsing:
  ```python
  i = len(name)
  while i > 0 and name[i - 1].isdecimal():
      i -= 1
  if 0 < i < len(name) and all(c.isalpha() for c in name[:i]):
      subs.insert(0, name[i:])
      name = name[:i]
  ```

**Codex review:** Suggested using `isdecimal()` instead of `isdigit()` to avoid misclassifying superscript digits (², ³) as subscripts.

**Gate result:** ✓ GREEN
- test_super_sub: PASS
- All FAIL_TO_PASS tests now passing

**Trajectory:** Convergent success - single iteration fix


## Audit: sympy__sympy-20916

### FAIL_TO_PASS
- test_super_sub: **PASS** ✓

### PASS_TO_PASS
- test_requires_partial: **PASS** ✓

### Regressions
None

### Pre-existing failures (not counted)
None — all expected failures properly marked

### Gate output
```
test_super_sub ok
test_requires_partial ok
test_requires_partial_unspecified_variables f
======== tests finished: 2 passed, 1 expected to fail, in 0.03 seconds =========
```

### Analysis
The craft patch successfully resolved the issue:
1. Replaced ASCII-only regex `[a-zA-Z]+[0-9]+` with Unicode-aware `.isalpha()` and `.isdecimal()`
2. test_super_sub now passes (was failing on base with Unicode digits)
3. test_requires_partial still passes (no regression)
4. All contract requirements met: FAIL_TO_PASS passes, PASS_TO_PASS still passes, zero regressions

