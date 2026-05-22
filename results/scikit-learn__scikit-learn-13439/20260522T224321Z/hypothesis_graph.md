# Hypothesis graph: scikit-learn__scikit-learn-13439

## Hypothesis H₀ — Missing __len__ method (deduction, 99%)

**Timestamp**: 2026-05-22 (first diagnosis)

**Observation**: Test fails with `TypeError: object of type 'Pipeline' has no len()` when calling `len(pipeline)`.

**Root cause**: Pipeline class has `__getitem__` for indexing/slicing (commit 22071218b) but lacks `__len__` method. Python's `len()` built-in requires `__len__` to be defined. Since Pipeline stores steps in `self.steps` (a list), `__len__` should return `len(self.steps)`.

**Evidence**:
- `sklearn/pipeline.py:202-222` — `__getitem__` exists, uses `self.steps[ind]`
- `sklearn/pipeline.py:131` — `self.steps` initialized as list
- `sklearn/tests/test_pipeline.py:1072` — test expects `len(pipeline) == 2`

**Edit site**: `sklearn/pipeline.py` line 223 — add `__len__` method returning `len(self.steps)`

**Confidence**: deduction — 99%

## Gate Loop - Iteration 1

**Action**: Added `__len__` method to Pipeline class at line 222 in `sklearn/pipeline.py`

**Diff**:
```python
def __len__(self):
    """Return the number of steps in the pipeline."""
    return len(self.steps)
```

**Volley with codex**: Confirmed implementation correct, improved docstring to match project style ("Return" instead of "Returns").

**Gate result**: ✅ PASSED  
- All 41 tests passed (0.92s)
- FAIL_TO_PASS test `test_make_pipeline_memory` now passes
- No regressions observed

**Trajectory**: Convergent-success (immediate resolution)

**Resolution**: The recon diagnosis was accurate. Adding `__len__` to return `len(self.steps)` was the complete fix.

## Audit: scikit-learn__scikit-learn-13439

**Timestamp**: 2026-05-22 (audit verification)

### Phase 1: Patch confirmation
- Patch is live: `sklearn/pipeline.py` (+4 lines)
- Added `__len__` method to Pipeline class

### Phase 2: Gate execution
- Command: `/tmp/gate-scikit-learn_scikit-learn-13439`
- Result: 41 passed, 2 warnings in 0.95s

### Phase 3: Classification

#### FAIL_TO_PASS
- `sklearn/tests/test_pipeline.py::test_make_pipeline_memory`: **PASS** ✓

#### PASS_TO_PASS regressions
**None** — all PASS_TO_PASS tests remain passing.

#### Pre-existing (not counted, confirmed against base capture)
**None** — the only failure in the base capture was the FAIL_TO_PASS test.

### Phase 4: Verdict
All FAIL_TO_PASS tests pass (1/1) and zero PASS_TO_PASS regressions.

**Contract satisfied**: ✅

VERDICT: RESOLVED
RE-ENTER: none
