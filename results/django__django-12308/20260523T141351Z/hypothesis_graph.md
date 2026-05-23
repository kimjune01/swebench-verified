# Hypothesis graph: django__django-12308

## H₀ — Initial diagnosis (deduction, 99%)

**Failure mode:** `display_for_field` returns Python repr instead of JSON format for JSONField values

**Root cause:** `django/contrib/admin/utils.py:display_for_field` (lines 380-402) lacks special case for `models.JSONField`. Execution falls through to `display_for_value` which formats based on Python value type:
- Lists → comma-separated string (line 420)
- Dicts → Python repr via `str()` (line 422)

**Evidence:**
- Test output: `AssertionError: "{'a': {'b': 'c'}}" != '{"a": {"b": "c"}}'`
- Code trace: no `isinstance(field, models.JSONField)` check in function
- `display_for_value:420` — `isinstance(value, (list, tuple))` formats as `', '.join()`
- `display_for_value:422` — `else: return str(value)` for dicts

**Edit sites:**
1. `django/contrib/admin/utils.py:1-30` — add `import json`
2. `django/contrib/admin/utils.py:399-401` — insert `elif isinstance(field, models.JSONField):` clause before final `else`
   - Logic: handle `InvalidJSONInput` → try `json.dumps(value, cls=field.encoder)` → catch TypeError/ValueError → fallback `str(value)`

**Status:** proposed

## Gate Loop Node 1 - Initial Fix

**Iteration**: 1
**Timestamp**: 2026-05-23

**Change Applied**:
Added JSONField handling to `display_for_field` function in `django/contrib/admin/utils.py`:
1. Added `import json` to imports
2. Added JSONField branch before final else clause that:
   - Calls `json.dumps(value, cls=field.encoder)` to respect custom encoders
   - Falls back to `display_for_value(value, empty_value_display)` on TypeError for invalid JSON

**Gate Result**: ✅ PASS
- test_json_display_for_field (admin_utils.tests.UtilsTests) ... ok
- test_label_for_field (admin_utils.tests.UtilsTests) ... ok
- All 22 tests passed

**Trajectory**: Convergent success - first iteration resolved both FAIL_TO_PASS tests.

**Root Cause Validated**: The recon diagnosis was correct - `display_for_field` lacked JSONField handling and was falling through to `display_for_value`, which formatted based on Python types rather than JSON serialization.

**Resolution**: COMPLETE

## Audit Verification

**Date**: 2026-05-23
**Instance**: django__django-12308

### Phase 1: Patch Status
Craft patch is live:
```
django/contrib/admin/utils.py | 6 ++++++
1 file changed, 6 insertions(+)
```

### Phase 2: Gate Results
All 22 tests passed (0.028s).

### Phase 3: Classification

#### FAIL_TO_PASS
- test_json_display_for_field (admin_utils.tests.UtilsTests): **PASS** ✓
- test_label_for_field (admin_utils.tests.UtilsTests): **PASS** ✓

#### PASS_TO_PASS regressions
None. All 20 PASS_TO_PASS tests remain passing.

#### Pre-existing failures (confirmed against base capture)
On base, test_json_display_for_field had 3 parameterized failures:
- value={'a': {'b': 'c'}}: AssertionError: "{'a': {'b': 'c'}}" != '{"a": {"b": "c"}}'
- value=['a', 'b']: AssertionError: 'a, b' != '["a", "b"]'
- value='a': AssertionError: 'a' != '"a"'

Now passing with the patch — fix is effective.

### Phase 4: Verdict

**Contract fulfilled:**
- ✅ All FAIL_TO_PASS tests pass
- ✅ Zero PASS_TO_PASS regressions

VERDICT: RESOLVED
RE-ENTER: none
