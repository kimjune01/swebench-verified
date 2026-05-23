# Hypothesis graph: django__django-15503

## Node: H₀ (abduction)
**Timestamp**: 2026-05-23 (initial diagnosis)
**Status**: active hypothesis

**Symptom**: Tests `test_has_key_number` and `test_has_keys` fail when using has_key, has_keys, and has_any_keys lookups on JSONField with numeric string keys ("123", "456", "789", etc.) on SQLite. Expected to find objects but return empty querysets.

**Failure mode**: Wrong query results - lookups don't match objects that have numeric string keys.

**Root cause**: The `compile_json_path` function (line 129-143) treats any string that can be converted to an integer as an array index, generating paths like `$[123]` instead of `$."123"`. When `HasKeyLookup.as_sql` (line 200) uses `compile_json_path` to build paths for RHS keys being checked, numeric string keys are incorrectly treated as array indices instead of object keys.

**Evidence**:
- `django/db/models/fields/json.py:129-143` - `compile_json_path` tries `int(key_transform)` and generates `[123]` for numeric strings
- `django/db/models/fields/json.py:200` - `HasKeyLookup.as_sql` calls `compile_json_path(rhs_key_transforms, include_root=False)` to build key paths
- SQLite test: `JSON_TYPE(data, '$[123]')` returns `None` but `JSON_TYPE(data, '$."123"')` returns `text` for `{"123": "value"}`

**Call path trace**:
1. `NullableJSONModel.objects.filter(value__has_key="123")` 
2. → `HasKey` lookup registered on JSONField
3. → `HasKeyLookup.as_sql` (line 174)
4. → `compile_json_path(["123"], include_root=False)` (line 200)
5. → Returns `"[123]"` instead of `."123"`
6. → Final path: `$[123]` (array access) instead of `$."123"` (object key)

**Suspect set**:
- `django/db/models/fields/json.py:170-230` - `HasKeyLookup` class and related lookups
- `django/db/models/fields/json.py:129-143` - `compile_json_path` function

**Confidence**: deduction - 95%
- Traced the exact code path from test to failure
- Verified SQLite behavior with direct SQL queries
- Confirmed the generated path is wrong

**Why PostgreSQL works**: `HasKeyLookup.as_postgresql` (lines 218-225) doesn't use `compile_json_path`; it uses the PostgreSQL `?` operator which takes keys as string parameters.

**Edit sites**:
1. `django/db/models/fields/json.py` lines 195-202 in `HasKeyLookup.as_sql`: Replace `compile_json_path(rhs_key_transforms, include_root=False)` with logic that always treats keys as object properties. Build key path by appending `."key"` for each key transform, never `[index]`.

Specific change needed:
```python
# Instead of:
rhs_params.append(
    "%s%s" % (
        lhs_json_path,
        compile_json_path(rhs_key_transforms, include_root=False),
    )
)

# Use:
key_path_parts = []
for key_transform in rhs_key_transforms:
    key_path_parts.append(".")
    key_path_parts.append(json.dumps(key_transform))
rhs_params.append(lhs_json_path + "".join(key_path_parts))
```

**Verification path**: After fix, `has_key="123"` should generate SQL with path `$."123"` and the failing tests should pass.

## Craft gate loop

### Iteration 1: Initial fix attempt
**Change**: Modified `HasKeyLookup.as_sql` to force all RHS keys to use object notation `."key"` instead of array notation `[N]`.

**codex pre-gate review**: Flagged that the fix was too broad - it would break array indices in the middle of RHS paths. Suggested narrower fix: only force the final key to be an object key.

**Gate result**: FAIL_TO_PASS tests pass, but 6 other tests regressed:
- test_key_transform_expression
- test_key_transform_annotation_expression  
- test_nested_key_transform_expression
- test_nested_key_transform_annotation_expression
- test_nested_key_transform_on_subquery
- test_ordering_grouping_by_key_transform

### Iteration 2: Narrower fix
**Change**: Modified approach to only force final RHS key as object key: `"%s%s.%s" % (lhs_json_path, compile_json_path(rhs_key_transforms[:-1], include_root=False), json.dumps(rhs_key_transforms[-1]))`

**codex post-gate review**: Identified root cause of regressions - `KeyTransformIsNull.as_sqlite` uses `HasKey` internally to generate JSON paths, including for array indices like `value__d__0__isnull=False`. The fix was forcing `0` to be treated as object key `."0"` instead of array index `[0]`.

**Fix**: Modified `KeyTransformIsNull.as_sqlite` to build JSON paths directly using `compile_json_path` instead of delegating to `HasKey`, allowing array indices to work correctly.

**Gate result**: ✅ ALL PASS (88 tests, 8 skipped)

**FAIL_TO_PASS tests**:
- test_has_key_number ✓
- test_has_keys ✓

### Resolution
Fixed in 2 iterations. Changes:
1. `HasKeyLookup.as_sql`: Force final RHS key to always use object notation
2. `KeyTransformIsNull.as_sqlite`: Build paths directly instead of using `HasKey`

Converged with codex guidance on both iterations - codex caught the too-broad first attempt and diagnosed the KeyTransformIsNull conflict on the second.

## Audit: django__django-15503

### Phase 1: Patch verification
✓ Patch is live: `django/db/models/fields/json.py` modified (9 insertions, 7 deletions)

### Phase 2: Gate execution
Full test suite: `./tests/runtests.py --verbosity 2 --settings=test_sqlite --parallel 1 model_fields.test_jsonfield`

**Result**: 88 tests, 8 skipped, **0 failures**

### Phase 3: Classification against baseline

#### FAIL_TO_PASS results
- ✅ `test_has_key_number (model_fields.test_jsonfield.TestQuerying)` - **PASS**
- ✅ `test_has_keys (model_fields.test_jsonfield.TestQuerying)` - **PASS**

Both FAIL_TO_PASS tests now pass. On baseline, these had 4 sub-test failures each (testing numeric string keys "123", "456", "789", "000", "777", "999").

#### PASS_TO_PASS regressions
**None**. All PASS_TO_PASS tests remain passing.

#### Pre-existing failures
**None**. The baseline showed only the 2 FAIL_TO_PASS tests failing.

### Phase 4: Verdict
All FAIL_TO_PASS tests pass ✓  
Zero PASS_TO_PASS regressions ✓

**Contract satisfied**: The patch resolves the issue without introducing new failures.

