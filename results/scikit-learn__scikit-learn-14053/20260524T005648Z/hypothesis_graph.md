# Hypothesis graph: scikit-learn__scikit-learn-14053

## H₀: Initial observation (abduction)
**Status**: Confirmed as root cause
**Type**: Abduction → Deduction (verified by code inspection and test)
**Claim**: The tests fail because `export_text` in `sklearn/tree/export.py` raises `IndexError: list index out of range` when building the `feature_names_` list for trees with a single feature.

**Evidence**:
- Stack trace shows error at `sklearn/tree/export.py:893`: `feature_names_ = [feature_names[i] for i in tree_.feature]`
- Failing test creates a single-feature dataset: `X_single = [[-2], [-1], [-1], [1], [1], [2]]` (shape: 6×1)
- Calls `export_text(reg, decimals=1, feature_names=['first'])` where `feature_names` has length 1
- `tree_.feature` for a simple tree is `[0, -2, -2]` (feature 0 at root, TREE_UNDEFINED=-2 for two leaf nodes)
- List comprehension tries `feature_names[-2]` which raises IndexError on a 1-element list

**Why this is a latent bug**:
- With 2+ features, `feature_names[-2]` accidentally works due to Python's negative indexing
- Example: `['a', 'b'][-2]` returns `'a'` (valid)
- But `['first'][-2]` raises IndexError (only 1 element, can't go back 2)
- This is why existing tests with multi-feature trees pass

**Root cause mechanism**:
Lines 893-895 in `sklearn/tree/export.py` build `feature_names_` by indexing `feature_names` with ALL values from `tree_.feature`, including leaf nodes that have `_tree.TREE_UNDEFINED` (-2). The code should skip or handle TREE_UNDEFINED values.

**Confidence**: Deduction — 99% (traced through code, reproduced failure, verified tree structure)

**Edit sites identified**:
- `sklearn/tree/export.py` lines 893-895: Must handle `_tree.TREE_UNDEFINED` when building `feature_names_` list

## Gate iteration 1 (PASS)

**Fix applied**: Modified `sklearn/tree/export.py` lines 893 and 895 to handle `_tree.TREE_UNDEFINED` values in the list comprehensions that build `feature_names_`.

**Change**:
```python
# Before:
feature_names_ = [feature_names[i] for i in tree_.feature]
feature_names_ = ["feature_{}".format(i) for i in tree_.feature]

# After:
feature_names_ = [
    feature_names[i] if i != _tree.TREE_UNDEFINED else None
    for i in tree_.feature
]
feature_names_ = [
    "feature_{}".format(i) if i != _tree.TREE_UNDEFINED else None
    for i in tree_.feature
]
```

**Rationale**: Leaf nodes have `tree_.feature[node] = TREE_UNDEFINED (-2)`. Indexing `feature_names[-2]` on a single-element list raises IndexError. The fix checks for `TREE_UNDEFINED` before indexing. Since `feature_names_[node]` is only accessed when `tree_.feature[node] != TREE_UNDEFINED` (line 930), the `None` placeholder for leaf nodes is never used.

**Gate result**: PASS
- `test_export_text`: **PASSED** ✓
- Unrelated matplotlib setup errors in `test_plot_tree_*` (not regression from this fix)

**Trajectory**: Convergent success on first iteration.

## Audit: scikit-learn__scikit-learn-14053

**Patch verification**: Live in tree (sklearn/tree/export.py: +8, -2)

### FAIL_TO_PASS
- `test_export_text`: **PASSED** ✓

### PASS_TO_PASS regressions
None.

### Pre-existing failures (not counted, confirmed against base capture)
- `test_plot_tree_entropy`: ERROR - `TypeError: use() got an unexpected keyword argument 'warn'` in sklearn/conftest.py:18 (matplotlib.use compatibility issue — identical to baseline)
- `test_plot_tree_gini`: ERROR - same matplotlib.use compatibility issue (identical to baseline)

### Full gate results
```
6 passed, 1 warning, 2 errors in 0.24s
```

All FAIL_TO_PASS tests pass. All PASS_TO_PASS tests pass. The two errors are pre-existing (same matplotlib.use API incompatibility present in fail-on-base capture).

**VERDICT**: RESOLVED
**RE-ENTER**: none
