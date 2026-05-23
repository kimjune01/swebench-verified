# Hypothesis graph: django__django-13121

## Hypothesis Node: Duration Expression String Conversion Issue
**Status**: Active diagnosis  
**Type**: Abduction (85% confidence)  
**Timestamp**: 2026-05-23

### Failure Summary
The test `test_duration_expressions` fails when annotating with duration expressions like `F('estimated_time') + delta` on SQLite (and MySQL). The error occurs during result conversion:

```
TypeError: unsupported type for timedelta microseconds component: str
  File "/testbed/django/db/backends/base/operations.py", line 583, in convert_durationfield_value
    return datetime.timedelta(0, 0, value)
```

### Root Cause
`convert_durationfield_value` expects integer microseconds but receives string duration representations from expressions.

**Normal field retrieval path** (works):
1. DurationField stored as bigint microseconds (SQLite/MySQL lack native duration support)
2. `convert_durationfield_value(value, ...)` receives integer microseconds
3. Returns `datetime.timedelta(0, 0, value)` ✓

**Expression path** (fails on SQLite):
1. `F('estimated_time') + delta` generates `django_format_dtdelta(...)` SQL
2. `_sqlite_format_dtdelta` function returns `str(timedelta)` e.g., "1 day, 0:00:30.253000"
3. `convert_durationfield_value(value, ...)` receives string
4. Tries `datetime.timedelta(0, 0, "1 day, ...")` ✗ TypeError

**MySQL**: Uses base `combine_duration_expression` (no override), but stores as bigint microseconds. Expression results may also return as strings.

### Supporting Evidence
- `django/db/backends/sqlite3/base.py:167-184` - `_sqlite_format_dtdelta` returns `str(out)`
- `django/db/backends/sqlite3/operations.py:339-345` - `combine_duration_expression` uses `django_format_dtdelta`
- `django/db/backends/base/operations.py:581-583` - `convert_durationfield_value` only handles integers
- `django/db/models/fields/__init__.py:2353-2358` - DurationField's `get_db_converters` registers the converter for non-native backends
- `django/utils/dateparse.py:28-37` - `standard_duration_re` pattern matches str(timedelta) format

### Edit Sites
1. **django/db/backends/base/operations.py lines 1-11** - Add `parse_duration` import
   - Current: No import of `parse_duration`
   - Change: Add `from django.utils.dateparse import parse_duration` to imports

2. **django/db/backends/base/operations.py lines 581-583** - Fix `convert_durationfield_value` to handle strings
   - Current: Assumes value is always integer microseconds
   - Change: Check if value is string, parse with `parse_duration`, else use as microseconds

### Rejected Hypotheses
None - first iteration

### Open Questions
- Does MySQL have the exact same issue or a variant?
- Are there other expression types that might produce string durations?


## Gate loop: craft iteration 1

**Drafted fix**: Modified `convert_durationfield_value` to handle string durations by checking `isinstance(value, str)`, then trying `int(value)` for numeric microsecond strings, falling back to `parse_duration()` for expression result strings.

**codex volley (pre-gate)**: Caught two critical bugs in naive approach:
1. Simple string check would corrupt numeric microsecond strings (e.g., "1000000" → 1M seconds not microseconds)
2. Invalid strings would silently become None instead of raising errors

**Revised fix**: Added try/except to parse numeric string microseconds first, fall back to parse_duration only on ValueError, preserve error for unparseable values.

**Applied changes**:
- Added import: `from django.utils.dateparse import parse_duration`
- Modified `convert_durationfield_value` with proper string handling

**Gate result**: ✅ PASS - test_duration_expressions passes
```
test_duration_expressions (expressions.tests.FTimeDeltaTests) ... ok
Ran 1 test in 0.006s
OK
```

**Trajectory**: Convergent success (first iteration)


## Audit: django__django-13121

### Phase 1: Patch Confirmation
Patch is live in the tree:
```
django/db/backends/base/operations.py | 10 ++++++++++
1 file changed, 10 insertions(+)
```

### Phase 2: Full Gate Execution
Ran full test suite via `/tmp/gate-django_django-13121`:
```
Ran 173 tests in 0.209s
OK (skipped=4)
```

### Phase 3: Result Classification

#### FAIL_TO_PASS
- ✅ `test_duration_expressions (expressions.tests.FTimeDeltaTests)` - **PASS**

#### PASS_TO_PASS Regressions
**None** - All 173 tests passed with 0 failures, 0 errors.

#### Pre-existing Failures
**None** - Clean gate run.

### Applied Patch
```diff
+from django.utils.dateparse import parse_duration

 def convert_durationfield_value(self, value, expression, connection):
     if value is not None:
+        if isinstance(value, str):
+            # Try parsing as microseconds first (numeric string storage)
+            try:
+                return datetime.timedelta(0, 0, int(value))
+            except ValueError:
+                # Fall back to parsing duration string from expressions
+                parsed = parse_duration(value)
+                if parsed is not None:
+                    return parsed
         return datetime.timedelta(0, 0, value)
```

### Verdict Analysis
- All FAIL_TO_PASS tests pass: ✅
- Zero PASS_TO_PASS regressions: ✅
- Pre-existing failures: None
- Patch correctly handles both integer microseconds and string duration expressions
- No negative interactions with existing functionality

**VERDICT**: RESOLVED
**RE-ENTER**: none
