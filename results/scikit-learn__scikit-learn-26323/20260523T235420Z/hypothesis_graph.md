# Hypothesis graph: scikit-learn__scikit-learn-26323

---

## Hypothesis H₁ (Initial diagnosis)

**Type:** Deduction  
**Confidence:** 98%

**Claim:** `ColumnTransformer.set_output` does not propagate output configuration to the remainder transformer because the remainder is stored separately in `self.remainder`, not in `self.transformers` list.

**Evidence:**
1. Test failure: Column "a" has dtype `int64` instead of expected `bool`, indicating remainder output is numpy array not pandas DataFrame
2. Code inspection at `sklearn/compose/_column_transformer.py:296-302` shows `set_output` only iterates through `self.transformers` and `self.transformers_`
3. Code at line 245 shows `self.remainder = remainder` — stored separately from transformers list
4. Experimental verification: After `ct.set_output(transform="pandas")`, the remainder object has no `_sklearn_output_config` attribute, while transformers in the list do have it set to `{'transform': 'pandas'}`

**Edit required:**
In `sklearn/compose/_column_transformer.py` lines 296-304, after the loop calling `_safe_set_output` on transformers, add:
```python
if self.remainder not in {"passthrough", "drop"}:
    _safe_set_output(self.remainder, transform=transform)
```

**Status:** Active (awaiting craft)

## /craft Gate Loop

**Iteration 1: Draft and volley**

Recon diagnosis: `self.remainder` doesn't get output configuration when `set_output` is called before fitting because it's stored separately from `self.transformers`.

**Proposed fix:** Add `_safe_set_output(self.remainder, transform=transform)` in the `set_output` method after the existing transformer loop, guarded by a check that `self.remainder` is not "passthrough" or "drop".

**codex review feedback:**
- Suggested safer comparison style: use direct equality checks (`self.remainder != "passthrough" and self.remainder != "drop"`) instead of set membership
- Raised concerns about cloning and whether config survives, but noted this is a pre-fit test case
- Suggested the fix targets the pre-fit case (set_output then fit_transform)

**Applied fix:**
```python
# Also set output for remainder if it is a transformer
if self.remainder != "passthrough" and self.remainder != "drop":
    _safe_set_output(self.remainder, transform=transform)
```

**Gate result:** ✅ PASSED - all 189 tests passed, including `test_remainder_set_output`

**Evidence trajectory:** Convergent success - the fix directly addressed the root cause and the test passed on first gate run.

**Resolution:** The fix correctly handles the case where `set_output` is called before fitting by ensuring `self.remainder` gets the output configuration propagated to it, just like the other transformers.

---

## Audit: scikit-learn__scikit-learn-26323

**Patch confirmed live:**
```
sklearn/compose/_column_transformer.py | 4 insertions(+)
```

**Full gate results:** 189 passed in 0.75s

### FAIL_TO_PASS
- `test_remainder_set_output`: ✅ **PASS**

### PASS_TO_PASS regressions
None. All 189 tests passed with zero failures.

### Pre-existing failures (not counted)
None detected. Clean gate run on the patched tree.

### Classification summary

The single FAIL_TO_PASS test (`test_remainder_set_output`) now passes. Zero regressions introduced. The patch correctly propagates `set_output()` configuration to the remainder transformer by adding a guarded call to `_safe_set_output(self.remainder, transform=transform)` in the `ColumnTransformer.set_output` method.

The fix is minimal, targeted, and addresses the root cause identified in recon: `self.remainder` was stored separately from `self.transformers` and wasn't included in the output configuration propagation loop.

VERDICT: RESOLVED
RE-ENTER: none
