# Hypothesis graph: sympy__sympy-13031

## H₀: Initial observation (abduction)
The tests fail because `SparseMatrix.hstack` with zero-row matrices of widths [0,1,2,3] returns shape (0, 3) instead of (0, 6).
Mode: abduction
Confidence: 95%

## H₁: Root cause - incorrect empty matrix check (deduction)
**Root cause:** The `row_join` and `col_join` methods in `sympy/matrices/sparse.py` use `if not self:` to check if a matrix is "empty". This evaluates to True for ANY matrix with `rows * cols == 0`, not just matrices with zero width (for row_join) or zero height (for col_join).

**Evidence:**
- `sympy/matrices/sparse.py:1194` - row_join uses `if not self:` which returns `type(self)(other)` when self has zero elements
- `sympy/matrices/sparse.py:988` - col_join uses the same pattern
- When hstacking (0,0), (0,1), (0,2), (0,3): each has len=0, so reduce repeatedly returns just the current `other`, discarding accumulated width

**Why this breaks:**
- `__len__` returns `rows * cols`, so (0,1), (0,2), etc. all have len=0 and are treated as "empty"
- `hstack` uses `reduce(row_join, ...)`, so (0,0).row_join((0,1)) correctly gives (0,1), but then (0,1).row_join((0,2)) returns `type(self)((0,2))` = (0,2) instead of (0,3)

**Correct behavior (from base class in common.py):**
- `row_join` should check `if self.cols == 0:` (zero width), not `if not self:`
- `col_join` should check `if self.rows == 0:` (zero height), not `if not self:`

Mode: deduction (traced through code logic)
Confidence: 99%

## Craft gate loop

### Iteration 1: Initial fix volleyed with codex

**Draft fix:** Changed `if not self:` to `if self.rows == 0:` in col_join and `if self.cols == 0:` in row_join.

**codex feedback:** Too broad — skips shape validation for zero-dimension matrices. For example, `(0, 1).col_join((2, 2))` would return `(2, 2)` instead of raising ShapeError. Should only treat `(0, 0)` as identity element.

**Revised fix:** Changed to `if self.rows == 0 and self.cols == 0:` for both methods.

**codex feedback:** Looks correct for the failing test. Only handles left-hand identity (not two-sided), which matches test requirements.

### Iteration 2: Applied and gated

**Applied changes:**
- Line 988 (col_join): `if not self:` → `if self.rows == 0 and self.cols == 0:`
- Line 1194 (row_join): `if not self:` → `if self.rows == 0 and self.cols == 0:`

**Gate result:** ✅ ALL TESTS PASSED (11 passed in 0.42s)

**Resolution:** The fix correctly treats only `(0, 0)` matrices as the identity element for join operations, allowing zero-dimension matrices with non-zero width or height to properly stack while preserving shape validation.

---

## Audit: sympy__sympy-13031

### FAIL_TO_PASS
- test_sparse_matrix: **PASS** ✅

### PASS_TO_PASS regressions
None. All PASS_TO_PASS tests passed:
- test_transpose: ok
- test_trace: ok
- test_CL_RL: ok
- test_add: ok
- test_errors: ok
- test_len: ok
- test_sparse_zeros_sparse_eye: ok
- test_copyin: ok
- test_sparse_solve: ok

### Pre-existing failures (not counted, confirmed against base capture)
None.

### Patch verification
```diff
diff --git a/sympy/matrices/sparse.py b/sympy/matrices/sparse.py
@@ -985,7 +985,7 @@ def col_join(self, other):
-        if not self:
+        if self.rows == 0 and self.cols == 0:
             return type(self)(other)
@@ -1191,7 +1191,7 @@ def row_join(self, other):
-        if not self:
+        if self.rows == 0 and self.cols == 0:
             return type(self)(other)
```

**Result:** All FAIL_TO_PASS tests now pass. Zero regressions. The fix correctly identifies only `(0,0)` matrices as the identity element for join operations, preserving proper shape validation for zero-dimension matrices with non-zero width or height.

