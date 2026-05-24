# Hypothesis graph: sympy__sympy-19637

## H₀: Indentation error causes UnboundLocalError
**Mode**: Deduction  
**Confidence**: 99%  
**Status**: Active

### Observation
Test `test_kernS` fails with:
```
UnboundLocalError: local variable 'kern' referenced before assignment
  File "/testbed/sympy/core/sympify.py", line 516, in kernS
    hit = kern in s
```

### Analysis
In `sympy/core/sympify.py`, the `kernS` function has a scoping bug:
- Line 503-508: `if ' ' in s:` block defines `kern` variable
- Line 516: `hit = kern in s` references `kern` but is OUTSIDE the if block (wrong indentation)
- When input has no spaces after transformations (e.g., `"(2*x)/(x-1)"`), the if block is skipped
- `kern` is never defined, but line 516 tries to use it → UnboundLocalError

Traced through test case `"(2*x)/(x-1)"`:
1. After stripping spaces: `"(2*x)/(x-1)"`
2. After `s.replace('*(', '* *(')`: no change (no `*(` pattern)
3. After `s.replace('-(', ...)`: no change (no `-(` pattern)
4. Result: `' ' in s` is False
5. Lines 504-508 skipped, `kern` never defined
6. Line 516 → UnboundLocalError

### Supporting Evidence
- `sympy/core/sympify.py:503-508` - `kern` defined inside if block (12-space indent)
- `sympy/core/sympify.py:516` - `hit = kern in s` outside if block (8-space indent)
- Confirmed via `cat -A` that line 516 has 8 spaces (same level as `if`), not 12 (inside block)

### Edit Site
`sympy/core/sympify.py` line 516: Change indentation from 8 spaces to 12 spaces to move inside the `if ' ' in s:` block.

### Rejected Alternatives
None - the root cause is unambiguous from the stack trace and code inspection.

## Craft gate loop

### Iteration 1 — volley + apply + gate

**Drafted fix:** Indented line 516 from 8 spaces to 12 spaces to move `hit = kern in s` inside the `if ' ' in s:` block.

**codex review:** Confirmed the fix preserves the no-space path by leaving `hit == False` when the conditional doesn't execute. Applied via Python script in container.

**Gate result:** ✅ PASS
- `test_kernS` now passes (was UnboundLocalError, now ok)
- Baseline had 3 exceptions (`test_evaluate_false`, `test_issue_17811`, `test_kernS`)
- Current run has 2 exceptions (only the first two — not regressions, pre-existing)
- FAIL_TO_PASS satisfied: `test_kernS` ✅

**Resolution:** Green gate on first iteration.

---

# Audit: sympy__sympy-19637

## FAIL_TO_PASS
- test_kernS: **PASS** ✓ (was UnboundLocalError on base, now ok)

## PASS_TO_PASS regressions
None - all PASS_TO_PASS tests continue passing.

## Pre-existing failures (not counted, confirmed against base capture)
- test_issue_16772 (f on base, f on patched)
- test_evaluate_false (E on base, E on patched)
- test_sympify_rational_numbers_set (f on base, f on patched)
- test_issue_17811 (E on base, E on patched)

## Patch analysis
```diff
diff --git a/sympy/core/sympify.py b/sympy/core/sympify.py
@@ -513,7 +513,7 @@ def kernS(s):
             while kern in s:
                 kern += choice(string.ascii_letters + string.digits)
             s = s.replace(' ', kern)
-        hit = kern in s
+            hit = kern in s
```

The fix correctly indents `hit = kern in s` to move it inside the `if ' ' in s:` block at line 503, ensuring `kern` is defined before use. This resolves the UnboundLocalError without introducing any regressions.

VERDICT: RESOLVED
RE-ENTER: none
