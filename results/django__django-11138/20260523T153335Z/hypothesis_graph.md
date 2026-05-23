# Hypothesis graph: django__django-11138

## Hypothesis Node: Initial Diagnosis (Abduction, 85%)

### Failure Summary
Test `test_query_convert_timezones` fails because `__date` lookups incorrectly assume database datetimes are stored in UTC, ignoring the database's TIME_ZONE setting. When `Event.objects.filter(dt__date=event_datetime.date())` executes with database timezone set to 'Africa/Nairobi', it returns None instead of the expected event.

### Suspect Set
1. `django/db/backends/mysql/operations.py` lines 73-76: `_convert_field_to_tz` method
2. `django/db/backends/oracle/operations.py` lines 97-104: `_convert_field_to_tz` method  
3. `django/db/backends/sqlite3/base.py` line 77: `_sqlite_datetime_parse` function
4. `django/db/backends/sqlite3/operations.py` lines 90-108: datetime SQL generation methods

### Root Cause
All three backends (MySQL, SQLite, Oracle) hardcode UTC as the source timezone when converting database datetime fields to dates/times, instead of using `connection.timezone_name`:

**MySQL**: Line 75 hardcodes 'UTC':
```python
field_name = "CONVERT_TZ(%s, 'UTC', '%s')" % (field_name, tzname)
```

**Oracle**: Line 104 hardcodes UTC offset '0:00':
```python
return "CAST((FROM_TZ(%s, '0:00') AT TIME ZONE '%s') AS TIMESTAMP)" % (field_name, tzname)
```

**SQLite**: `typecast_timestamp()` creates datetimes in UTC, then `_sqlite_datetime_parse` converts to target timezone, effectively treating all database values as UTC-based.

### Confidence
**Abduction - 85%**: Pattern matches the problem description exactly. Code inspection confirms UTC is hardcoded in all three backends. The connection object provides `timezone_name` and `timezone` properties specifically for this purpose, used elsewhere in the same files (e.g., `adapt_datetimefield_value`, `convert_datetimefield_value`).

### Supporting Evidence
- `django/db/backends/mysql/operations.py:75` - `"CONVERT_TZ(%s, 'UTC', '%s')"` hardcodes 'UTC'
- `django/db/backends/oracle/operations.py:104` - `"FROM_TZ(%s, '0:00')"` hardcodes UTC offset  
- `django/db/backends/utils.py:typecast_timestamp` - `tzinfo = utc if settings.USE_TZ else None` hardcodes UTC
- `django/db/backends/base/base.py:117-133` - `connection.timezone` and `connection.timezone_name` properties exist and return database TIME_ZONE setting
- Test helper `override_database_connection_timezone` sets `connection.settings_dict['TIME_ZONE']` and clears cached `connection.timezone`/`connection.timezone_name`

### Edit Sites

**MySQL** (1 location):
- `django/db/backends/mysql/operations.py:73-76` - In `_convert_field_to_tz`, replace `'UTC'` with `self.connection.timezone_name`

**Oracle** (1 location):  
- `django/db/backends/oracle/operations.py:97-104` - In `_convert_field_to_tz`, replace `'0:00'` with database timezone representation

**SQLite** (8+ locations):
- `django/db/backends/sqlite3/operations.py:90-108` - Update `datetime_cast_date_sql`, `datetime_cast_time_sql`, `datetime_extract_sql`, `datetime_trunc_sql` to pass `self.connection.timezone_name` as database timezone parameter
- `django/db/backends/sqlite3/base.py` - Update function registrations and implementations of `_sqlite_datetime_parse`, `_sqlite_datetime_cast_date`, `_sqlite_datetime_cast_time`, `_sqlite_datetime_extract`, `_sqlite_datetime_trunc` to accept and use database timezone instead of assuming UTC


## Craft iteration 1

**Approach**: Implemented the fix from recon diagnosis:
- MySQL: Changed `CONVERT_TZ` to use `self.connection.timezone_name` instead of hardcoded 'UTC'
- Oracle: Changed `FROM_TZ` to use `self.connection.timezone_name` instead of '0:00'  
- SQLite: Added `db_tzname` parameter to datetime cast/extract/trunc functions; created `_sqlite_datetime_parse_tz` helper to reinterpret naive datetime values as being in the database timezone instead of UTC

**Volley**: Consulted codex before implementation. Key feedback:
- SQLite arity changes are high-risk - must update all call sites and registrations together
- Handle None db_tzname (when USE_TZ=False) - fallback to original behavior
- Use timezone.make_aware instead of raw pytz.localize for DST safety
- connection.timezone_name already has UTC fallback when None

**Gate result**: PASS
- test_query_convert_timezones: ✓ PASSING (FAIL_TO_PASS met)
- 84 tests run, 3 unrelated failures in SerializationTests (SimpleTestCase, no database)
- All NewDatabaseTests passing including the target test

**Trajectory**: Convergent success - FAIL_TO_PASS test now passes on first gate run after fixing implementation details.

**Resolution**: ✓ RESOLVED

## Audit: django__django-11138

### Patch Status
Patch confirmed live:
- 4 files changed: `mysql/operations.py`, `oracle/operations.py`, `sqlite3/base.py`, `sqlite3/operations.py`
- 61 insertions, 22 deletions

### FAIL_TO_PASS Results
- `test_query_convert_timezones (timezones.tests.NewDatabaseTests)` - **PASS** ✓

### PASS_TO_PASS Status
- All PASS_TO_PASS tests verified passing
- Zero regressions detected

### Pre-existing Failures (not counted, confirmed against base capture)
The following tests were already failing on base and continue to fail:
- `test_aware_datetime_in_local_timezone (timezones.tests.SerializationTests)` - FAIL (pre-existing)
- `test_aware_datetime_in_other_timezone (timezones.tests.SerializationTests)` - FAIL (pre-existing)
- `test_aware_datetime_with_microsecond (timezones.tests.SerializationTests)` - FAIL (pre-existing)

These are SerializationTests that were failing in the baseline capture and are not related to the `__date` lookup timezone conversion issue that this patch addresses.

### Gate Summary
- Total tests run: 84
- Failures: 3 (all pre-existing)
- Skipped: 8
- **All FAIL_TO_PASS tests now pass**
- **Zero new regressions introduced**

VERDICT: RESOLVED
RE-ENTER: none
