# Hypothesis graph: pallets__flask-5014

## H₀: Missing empty name validation (abduction)

**Observation**: Test `test_empty_name_not_allowed` fails because `flask.Blueprint("", __name__)` does not raise ValueError.

**Failure mode**: The test expects a ValueError when creating a Blueprint with an empty string name, but no exception is raised. The Blueprint is created successfully with an empty name.

**Trace**: 
- Test calls `flask.Blueprint("", __name__)` at `tests/test_blueprints.py:261`
- Blueprint.__init__ at `src/flask/blueprints.py:172-196` accepts the empty name without validation
- Line 193-194 validates that name doesn't contain dots, but there's no check for empty strings
- Line 196 assigns `self.name = name` without validation

**Root cause hypothesis**: The Blueprint.__init__ method (src/flask/blueprints.py:172-196) validates that the name parameter doesn't contain dots (line 193-194) but lacks validation to ensure the name is non-empty. An empty string passes through all checks and gets assigned to self.name.

**Supporting evidence**:
- `src/flask/blueprints.py:193-194` — Only validation is: `if "." in name: raise ValueError("'name' may not contain a dot '.' character.")`
- `src/flask/blueprints.py:196` — Name is assigned without empty check: `self.name = name`
- `tests/test_blueprints.py:255-256` — Similar validation test for dots exists and passes
- Problem statement references issue #4944 stating "Things do not work correctly if a Blueprint is given an empty name"

**Edit site**: `src/flask/blueprints.py:193-196` — Add empty name validation before the dot validation

**Confidence**: Deduction — 99%

## Implementation (craft)

**Iteration 1**:
- **Draft**: Added `if name == "": raise ValueError("'name' may not be empty.")` before the existing dot check at line 193
- **Codex review**: Confirmed the approach but recommended using exact equality (`name == ""`) instead of truthiness check (`if not name`) to avoid rejecting other falsey values like `None`, and to match Flask's error message style ("may not" instead of "cannot")
- **Applied**: src/flask/blueprints.py:193-195 — Added empty string validation with proper error message
- **Gate result**: ✅ All 60 tests pass (60/60)
  - FAIL_TO_PASS: `test_empty_name_not_allowed` now passes
  - No regressions in PASS_TO_PASS tests

**Resolution**: The fix successfully validates empty Blueprint names. The minimal change (3 lines) ensures that `Blueprint("", __name__)` raises `ValueError("'name' may not be empty.")` while preserving all existing behavior.

## Audit (pallets__flask-5014)

### Patch confirmation
```
 src/flask/blueprints.py | 3 +++
 1 file changed, 3 insertions(+)
```

Patch is live. Added empty name validation to Blueprint.__init__

### FAIL_TO_PASS
- `tests/test_blueprints.py::test_empty_name_not_allowed`: **PASS** ✓

### PASS_TO_PASS regressions
None. All 59 PASS_TO_PASS tests remain passing.

### Pre-existing failures
None. All tests that were passing on base remain passing.

### Gate results
All 60 tests passed (60/60):
- The single FAIL_TO_PASS test now passes
- Zero regressions introduced
- Full test suite clean

### Classification
The patch successfully resolves the issue:
1. ✅ All FAIL_TO_PASS tests pass (1/1)
2. ✅ Zero PASS_TO_PASS regressions (0/59)
3. ✅ No new failures introduced

The fix adds a 3-line validation check (`if name == "": raise ValueError("'name' may not be empty.")`) before the existing dot validation in Blueprint.__init__. This minimal change correctly prevents empty blueprint names while preserving all existing behavior.

