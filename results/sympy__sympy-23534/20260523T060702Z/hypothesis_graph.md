# Hypothesis graph: sympy__sympy-23534

## H₀: Initial observation (abduction)
The test `test_symbols` fails because `symbols(('q:2', 'u:2'), cls=Function)[0][0]` returns a Symbol instead of an UndefinedFunction.

## H₁: Root cause identified (deduction)
When `symbols()` is called with a non-string iterable (tuple/list/set), it recursively calls `symbols()` for each element but fails to pass the `cls` parameter to the recursive call.

**Evidence:**
- File: `sympy/core/symbol.py`, lines 792-797
- Line 794: `result.append(symbols(name, **args))` 
- The function signature at line 586: `def symbols(names, *, cls=Symbol, **args) -> Any:`
- The `cls` parameter is keyword-only (after `*`) and is NOT included in `**args`
- The recursive call uses default `cls=Symbol` instead of the passed `cls=Function`

**Confidence:** deduction — 99%

The code path is:
1. `symbols(('q:2', 'u:2'), cls=Function)` is called
2. `isinstance(names, str)` is False (line 703)
3. Goes to else block (line 792)
4. Iterates over tuple elements (line 793)
5. Recursively calls `symbols('q:2', **args)` WITHOUT `cls=cls` (line 794)
6. Recursive call uses default `cls=Symbol` 
7. Returns tuple of Symbols instead of Functions

**Edit sites:**
- `sympy/core/symbol.py` line 794: Change `result.append(symbols(name, **args))` to `result.append(symbols(name, cls=cls, **args))`


## Craft Gate Loop

### Iteration 1

**Drafted fix:** Added `cls=cls` to the recursive call at line 794 in `sympy/core/symbol.py`

**Codex review:** Confirmed the fix is correct. The `cls` parameter is keyword-only and not captured in `**args`, so it must be explicitly passed in recursive calls. No issues found.

**Applied diff:**
```diff
--- a/sympy/core/symbol.py
+++ b/sympy/core/symbol.py
@@ -791,7 +791,7 @@ def symbols(names, *, cls=Symbol, **args) -> Any:
         return tuple(result)
     else:
         for name in names:
-            result.append(symbols(name, **args))
+            result.append(symbols(name, cls=cls, **args))
 
         return type(names)(result)
```

**Gate result:** ✅ PASS - All 13 tests passed including `test_symbols`

**Status:** RESOLVED

---

# Audit: sympy__sympy-23534

## FAIL_TO_PASS
- test_symbols: PASS ✓

## PASS_TO_PASS regressions
none

## Pre-existing (not counted, confirmed against base capture)
- test_disambiguate (was failing on base, now passing - bonus fix)

## Summary
The craft patch successfully resolves the issue. The fix adds `cls=cls` to the recursive `symbols()` call on line 794, ensuring the `cls` parameter is propagated through nested tuple unpacking. All target tests pass with zero regressions.

Patch diff:
```diff
-            result.append(symbols(name, **args))
+            result.append(symbols(name, cls=cls, **args))
```

VERDICT: RESOLVED
RE-ENTER: none
