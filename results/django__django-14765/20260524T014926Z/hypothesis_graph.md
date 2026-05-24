# Hypothesis graph: django__django-14765

## H₀ (Baseline - abduction)
The test `test_real_apps_non_set` fails because `ProjectState.__init__()` currently converts non-set iterables to sets instead of asserting that `real_apps` is already a set. When passed `real_apps=['contenttypes']`, no AssertionError is raised.

## Localization
**Suspect set:**
- `django/db/migrations/state.py` lines 92-97 (ProjectState.__init__ method)

**Call path:**
- Test: `tests/migrations/test_state.py:929` calls `ProjectState(real_apps=['contenttypes'])`
- Target: `django/db/migrations/state.py:95` checks `isinstance(real_apps, set)` and converts if not

## Root cause (deduction - 99%)
In `django/db/migrations/state.py`, the `ProjectState.__init__()` method (lines 92-97) currently checks if `real_apps` is a set and converts it if not:

```python
if real_apps:
    self.real_apps = real_apps if isinstance(real_apps, set) else set(real_apps)
else:
    self.real_apps = set()
```

According to the problem description, PR #14760 ensured all Django callers pass `real_apps` as a set. The requirement is to replace this conversion logic with an assertion that `real_apps` is a set when non-None.

**Evidence:**
- All production callers pass sets:
  - `django/db/migrations/loader.py:71` initializes `self.unmigrated_apps = set()`
  - `django/db/migrations/executor.py:69` passes `self.loader.unmigrated_apps`
  - `django/db/migrations/loader.py:338` passes `self.unmigrated_apps` to `graph.make_state()`
  - `django/db/migrations/graph.py:313` forwards that to `ProjectState(real_apps=...)`
  - Test cases use sets: `tests/migrations/test_state.py:919` passes `{'contenttypes'}`

**Fix specification:**
Replace the conversion logic with an assertion. When `real_apps` is not None, assert it's a set; otherwise initialize to `set()`.

## Edit sites
- `django/db/migrations/state.py` lines 94-96: Replace the conditional conversion with an assertion that `real_apps` is a `set` when truthy

Confidence: **deduction - 99%** (traced the code path, verified all callers, confirmed the test expectation)

## Craft: Gate Loop

### Iteration 1: Draft and Volley

**Initial draft:**
Changed lines 94-96 in `django/db/migrations/state.py` from:
```python
if real_apps:
    self.real_apps = real_apps if isinstance(real_apps, set) else set(real_apps)
else:
    self.real_apps = set()
```

To use explicit `None` check per codex feedback:
```python
if real_apps is None:
    self.real_apps = set()
else:
    assert isinstance(real_apps, set), "real_apps must be a set"
    self.real_apps = real_apps
```

**Codex critique:** Initial draft only asserted for truthy `real_apps`, leaving empty non-sets ([], (), frozenset()) silently converted via the else branch. Recommended explicit `None` check to fully enforce the internal API contract.

**Applied fix:** Used explicit `None` check as suggested by codex.

### Gate Result: ✅ PASS

All 65 tests passed in 0.059s, including:
- `test_real_apps_non_set` (FAIL_TO_PASS) ✅

**Resolution:** The fix correctly replaces defensive conversion with assertion. When `real_apps` is None, initializes to empty set. When `real_apps` is provided (including empty non-sets like []), asserts it must be a set, making the test `ProjectState(real_apps=['contenttypes'])` raise AssertionError as required.

**Trajectory:** Convergent success (1 iteration).

## Audit: django__django-14765

### Patch verification
```
django/db/migrations/state.py | 7 ++++---
1 file changed, 4 insertions(+), 3 deletions(-)
```

Patch replaces defensive conversion with assertion that `real_apps` must be a set when not None.

### FAIL_TO_PASS
- `test_real_apps_non_set (migrations.test_state.StateTests)`: **PASS** ✓

### PASS_TO_PASS regressions
None. All 64 PASS_TO_PASS tests remain passing.

### Pre-existing failures (not counted, confirmed against base capture)
None.

### Gate Result
```
Ran 65 tests in 0.058s
OK
```

All tests pass. The FAIL_TO_PASS test now raises AssertionError when `real_apps` is passed as a list instead of a set, fulfilling the requirement. No regressions introduced.

VERDICT: RESOLVED
RE-ENTER: none
