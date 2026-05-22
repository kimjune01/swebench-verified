# Hypothesis graph: pytest-dev__pytest-7324

## H0: Python 3.8+ rejects ast.Name nodes with True/False/None identifiers (abduction, 85%)

**Observation**: Tests fail with `ValueError: Name node can't be used with 'None' constant` when compiling expressions containing "True", "False", or "None".

**Root cause**: Python 3.8+ enforces that the literal constants True, False, and None cannot be used as identifiers in `ast.Name` nodes. The compile() function checks for these strings and:
- In debug builds: triggers assertion `compiler_nameop: Assertion '!_PyUnicode_EqualToASCIIString(name, "None") && ...' failed`
- In release builds: raises `ValueError: Name node can't be used with 'None' constant`

**Evidence**:
- `src/_pytest/mark/expression.py:164` creates `ast.Name(ident.value, ast.Load())` for ALL identifiers including "True", "False", "None"
- Direct test: `ast.Name("True", ast.Load())` compiled raises ValueError
- Workaround test: Using `ast.Subscript` to lookup via dict subscription works

**Fix approach**: Use `ast.Subscript` node for these three special constants to perform dict lookup (`__locals__["True"]`) instead of name binding, avoiding the Python restriction while maintaining the same lookup semantics.

**Confidence**: 85% (abduction) - tested workaround, clear error message, straightforward localization

## Craft gate loop - iteration 1

**Action**: Applied fix for True/False/None as mark identifiers

**Changes**:
1. Modified `not_expr()` to detect "True", "False", "None" identifiers and generate `ast.Subscript(__pytest_mark_eval__["identifier"])` instead of `ast.Name("identifier")`
2. Added KeyError handler in `MatcherAdapter.__getitem__()` for sentinel key "__pytest_mark_eval__"
3. Modified `Expression.evaluate()` to pass adapter both in globals dict (as "__pytest_mark_eval__") and as locals dict

**Technical details**:
- Used `ast.Index(ast.Str(...))` for Python 3.8 compatibility (pre-3.9 requires Index wrapper)
- Sentinel key "__pytest_mark_eval__" chosen as valid Python identifier unlikely to collide with user markers
- When eval() encounters `__pytest_mark_eval__["True"]`, it looks up the name in locals, falls through to globals (due to KeyError), retrieves the adapter object, and subscripts it to call the matcher

**Gate result**: ✅ PASS
```
============================== 83 passed in 0.05s ==============================
```

All FAIL_TO_PASS tests now pass:
- test_valid_idents[True] ✅
- test_valid_idents[False] ✅
- test_valid_idents[None] ✅

**Trajectory**: Convergent (success) - first attempt resolved the issue

---

# Audit: pytest-dev__pytest-7324

## FAIL_TO_PASS
- `testing/test_mark_expression.py::test_valid_idents[True]`: **PASS** ✓
- `testing/test_mark_expression.py::test_valid_idents[False]`: **PASS** ✓
- `testing/test_mark_expression.py::test_valid_idents[None]`: **PASS** ✓

## PASS_TO_PASS regressions
**None** — all 80 PASS_TO_PASS tests remain passing.

## Pre-existing failures (not counted, confirmed against base capture)
**None** — no pre-existing failures found in gate run.

## Summary
The craft patch successfully resolves all three FAIL_TO_PASS tests without introducing any regressions. The fix converts `True`, `False`, and `None` identifiers into `ast.Subscript` operations that look them up via the matcher function, avoiding Python 3.8+'s restriction on using these constants in `ast.Name` nodes.

All 83 tests passed in the full gate run:
- 3 FAIL_TO_PASS tests now PASS
- 80 PASS_TO_PASS tests remain PASS
- 0 regressions

VERDICT: RESOLVED
RE-ENTER: none
