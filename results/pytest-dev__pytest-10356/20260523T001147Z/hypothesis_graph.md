# Hypothesis graph: pytest-dev__pytest-10356

## H₀: Missing marks from multiple inheritance - get_unpacked_marks doesn't walk MRO
**Status:** Initial diagnosis  
**Mode:** Deduction (traced through code and reproduction)  
**Confidence:** 95%

### Failure symptom
Test `test_mark_mro` fails with:
```
AssertionError: assert <generator object normalize_mark_list at 0x...> == [Mark(name='xfail'...)]
```
Expected: `[xfail("c").mark, xfail("a").mark, xfail("b").mark]`  
Got: `[xfail("a").mark, xfail("c").mark]` (missing xfail("b"))

### Root cause
`get_unpacked_marks()` in `src/_pytest/mark/structures.py:358` only uses `getattr(obj, "pytestmark")`, which follows Python's normal attribute lookup. For a class `C(A, B)` with multiple inheritance:
1. Python's MRO for C is: `(C, A, B, object)`
2. `getattr(C, "pytestmark")` returns marks from C if C has its own pytestmark, otherwise from A (first base)
3. Marks from B are never collected

When `@xfail("c")` decorates C:
- `store_mark(C, mark)` calls `get_unpacked_marks(C)` 
- This returns A's marks (via inheritance)
- Then stores: `C.pytestmark = [...A's marks..., xfail("c")]`
- B's marks are lost

### Edit sites
1. **src/_pytest/mark/structures.py:358** - Add `consider_mro` parameter to `get_unpacked_marks`
   - Default `consider_mro=True` for backward compatibility
   - When True and obj is a class: walk `obj.__mro__` and collect `cls.__dict__.get("pytestmark", [])` from each
   - When False: only get marks from `obj.__dict__.get("pytestmark", [])` (direct, not inherited)
   - Order: own marks first, then MRO order

2. **src/_pytest/mark/structures.py:391** - Update `store_mark` to use `consider_mro=False`
   - Change `get_unpacked_marks(obj)` to `get_unpacked_marks(obj, consider_mro=False)`
   - This prevents copying inherited marks when storing new marks

### Supporting evidence
- `C.__mro__`: `(C, A, B, object)` — B is in MRO but marks not collected
- `A.__dict__["pytestmark"]`: `[xfail("a")]`
- `B.__dict__["pytestmark"]`: `[xfail("b")]`
- `C.__dict__["pytestmark"]`: `[xfail("a"), xfail("c")]` — contains A's marks, not B's

### Test expectations
- `get_unpacked_marks(C)` should return `[xfail("c"), xfail("a"), xfail("b")]`
- `get_unpacked_marks(C, consider_mro=False)` should return `[xfail("c")]` only


## Craft Gate Loop

### Gate Iteration 1
**Status:** PASS  
**FAIL_TO_PASS result:** `test_mark_mro` - PASSED  
**All tests:** 89 passed, 1 xfailed, 0 failed

**Changes applied:**
1. Modified `get_unpacked_marks()` in `src/_pytest/mark/structures.py`:
   - Added `consider_mro: bool = True` parameter
   - When `consider_mro=True` and obj is a class: walk `obj.__mro__` and collect marks from each class's `__dict__`
   - When `consider_mro=False` and obj is a class: return only marks from `obj.__dict__` (not inherited)
   - For non-class objects: use original `getattr` behavior
   - Convert result to list before returning

2. Modified `store_mark()` in `src/_pytest/mark/structures.py`:
   - Changed call to `get_unpacked_marks(obj, consider_mro=False)` to prevent copying inherited marks

**Codex feedback addressed:**
- Confirmed `inspect` was already imported
- Fixed indentation issues in the else branch
- Converted generator result to list for test compatibility

**Resolution:** The recon diagnosis was correct. The fix successfully makes marks from all base classes available through MRO traversal while preventing duplicate storage.


## Audit: pytest-dev__pytest-10356

**Run date:** 2026-05-22

### FAIL_TO_PASS
- `testing/test_mark.py::test_mark_mro`: **PASSED** ✓

### PASS_TO_PASS regressions
None - all 89 tests passing as expected.

### Pre-existing (not counted, confirmed against base capture)
- Three `test_marker_expr_eval_failure_handling` subtests show captured stderr errors in both baseline and gate output, but these tests PASS in both runs (they're testing error handling behavior, so the stderr is expected)

### Verdict summary
The craft patch successfully resolves the issue:
- The FAIL_TO_PASS test `test_mark_mro` now passes
- All PASS_TO_PASS tests remain passing (89 passed, 1 xfailed)
- No regressions introduced
- The fix correctly implements MRO traversal for mark collection while preventing duplicate storage

VERDICT: RESOLVED
RE-ENTER: none

