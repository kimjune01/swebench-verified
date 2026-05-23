# Hypothesis graph: scikit-learn__scikit-learn-25102

## Hypothesis Node: Initial Diagnosis (deduction, 98%)

**Instance**: scikit-learn__scikit-learn-25102

**Failure Mode**: DataFrame dtype information lost during pandas output wrapping

**Tests**:
- `sklearn/feature_selection/tests/test_base.py::test_output_dataframe`
- `sklearn/feature_selection/tests/test_feature_select.py::test_dataframe_output_dtypes`

**Error**: `AssertionError: assert dtype('O') == dtype('float32')` — output DataFrame columns have object dtype instead of preserving original dtypes (float32, category, etc.)

**Root Cause**:
When transformers use `set_output(transform="pandas")`, the `_wrap_in_pandas_container` function creates a new DataFrame without preserving the original dtypes. The flow:

1. Input DataFrame has specific dtypes (float32, category, etc.)
2. Input is converted to numpy array during validation (`check_array`)
3. Transform selects features from the array
4. Result is wrapped back to DataFrame via `_wrap_in_pandas_container`
5. **Line 62** of `sklearn/utils/_set_output.py`: `pd.DataFrame(data_to_wrap, index=index, columns=columns)` creates DataFrame without dtype argument
6. Pandas infers dtypes from the numpy array, which often has object dtype for mixed-type data

**Supporting Code**:
- `sklearn/utils/_set_output.py:62` — DataFrame creation without dtype preservation
- `sklearn/utils/_set_output.py:130-135` — Call to `_wrap_in_pandas_container` has access to `original_input` but doesn't use its dtypes

**Proposed Fix**:
1. Add `original_input` parameter to `_wrap_in_pandas_container`
2. Extract dtypes from `original_input` (if it's a DataFrame) for the output columns
3. Apply those dtypes to the created DataFrame before returning
4. Update call site in `_wrap_data_with_container` to pass `original_input`

**Classification**: Deduction — traced through code, reproduced behavior, identified exact line where dtype info is lost

**Status**: Ready for /craft

---

## [GATE LOOP - ITERATION 1] craft

**Status**: ✅ RESOLVED  
**Timestamp**: 2026-05-23

### Implementation

Applied fix to `sklearn/feature_selection/_base.py`:

1. **Added imports**:
   - `_safe_indexing` from `..utils`
   - `_get_output_config` from `..utils._set_output`

2. **Modified `transform()` method**:
   - Check if pandas output is configured AND input is a DataFrame
   - If yes, skip `_validate_data` to preserve the DataFrame (avoid conversion to ndarray)
   - Otherwise, call `_validate_data` as before

3. **Modified `_transform()` method**:
   - Handle empty selection for DataFrames: return `X.iloc[:, :0]` instead of `np.empty()`
   - Replace `X[:, safe_mask(X, mask)]` with `_safe_indexing(X, mask, axis=1)`
   - `_safe_indexing` handles both DataFrames (preserves dtypes via positional slicing) and arrays

### Codex Volley Summary

- **Round 1**: Initial wrapper-based approach rejected - too broad, would break transformers like StandardScaler
- **Round 2**: Opt-in flag approach rejected - still used name-based matching, duplicate column issues
- **Round 3**: DataFrame slicing in wrapper rejected - bypasses validation, no positional guarantee
- **Round 4**: Fix in SelectorMixin accepted - correct location, uses positional indexing, preserves dtypes naturally

### Gate Result

```
61 passed, 53 warnings in 1.31s
```

**FAIL_TO_PASS tests**:
- ✅ `sklearn/feature_selection/tests/test_base.py::test_output_dataframe`
- ✅ `sklearn/feature_selection/tests/test_feature_select.py::test_dataframe_output_dtypes`

### Root Cause Confirmed

The recon diagnosis was correct: `_wrap_in_pandas_container` created DataFrames from numpy arrays without dtype preservation. However, the fix wasn't in the wrapper - it was in `SelectorMixin` to prevent DataFrame→array→DataFrame round-trip by preserving the DataFrame through selection when pandas output is configured.


---

## [GATE LOOP - ITERATION 1] audit

**Timestamp**: 2026-05-23

### Phase 1: Patch Status

```
sklearn/feature_selection/_base.py | 32 ++++++++++++++++++++++++--------
1 file changed, 24 insertions(+), 8 deletions(-)
```

Patch is live in the container.

### Phase 2: Gate Execution

Full test suite run: **61 passed, 53 warnings in 1.29s**

### Phase 3: Classification

**FAIL_TO_PASS Results**:
- `sklearn/feature_selection/tests/test_base.py::test_output_dataframe` → **PASS** ✅
- `sklearn/feature_selection/tests/test_feature_select.py::test_dataframe_output_dtypes` → **PASS** ✅

**PASS_TO_PASS Results**:
All 59 PASS_TO_PASS tests remain passing. No regressions detected.

**Pre-existing Failures**:
None. The fail-on-base capture showed both FAIL_TO_PASS tests failing with:
```
AssertionError: assert dtype('O') == dtype('float32')
```

These are now resolved.

### Phase 4: Verdict

✅ **All FAIL_TO_PASS tests pass**: 2/2
✅ **Zero PASS_TO_PASS regressions**: 0/59
✅ **Contract fulfilled**

The fix successfully preserves DataFrame dtypes during feature selection by:
1. Detecting when pandas output is configured AND input is a DataFrame
2. Skipping array conversion to preserve DataFrame structure
3. Using `_safe_indexing` for column selection (handles DataFrames via iloc)
4. Returning properly-typed DataFrame slices

No kill report needed — patch resolves the issue cleanly.

