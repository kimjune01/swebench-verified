# Hypothesis graph: django__django-16662

## H₀ (abduction, 85%)
**Status**: Active  
**Claim**: Migration files generate imports sorted only by module name, not respecting Django coding style that requires `import X` statements before `from X import Y` statements.

**Evidence**:
- `django/db/migrations/writer.py:199-200` — sorting uses `key=lambda i: i.split()[1]` which extracts module name only
- Test expects: `import datetime\nimport time\nfrom django.db import migrations, models\n`
- Actual output: `import datetime\nfrom django.db import migrations, models\nimport time\n`
- When imports are `{import datetime, import time, from django.db import migrations, models}`:
  - Current key: `datetime` < `django.db` < `time` → puts `from` import in middle
  - Needed key: group by import type first, then module name → all `import` before all `from`

**Root cause**: Line 199 sorts by module name alone without distinguishing `import` vs `from` statements.

**Edit sites**:
- `django/db/migrations/writer.py:199` — change sort key to `lambda i: (i.startswith('from '), i.split()[1])` to group import types, then sort by module name

**Confidence**: 85% deduction — traced code path from test to failure, root cause is clear from reading the sorting logic.

## Craft gate loop

### Iteration 1: Initial fix applied

**Change**: Modified `django/db/migrations/writer.py` line 178 to sort imports by type first (import vs from), then by module name:
```python
sorted_imports = sorted(imports, key=lambda i: (i.startswith("from "), i.split()[1]))
```

**Codex volley**: Confirmed functional correctness, suggested double quotes for style consistency and comment update.

**Gate result**: ✅ PASS — All 52 tests passed, including `test_sorted_imports`

The fix works as designed:
- `import X` statements → `(False, module)` → sort first
- `from X import Y` statements → `(True, module)` → sort second  
- Within each group, sorted alphabetically by module name

Output now correctly produces:
```python
import datetime
import time
from django.db import migrations, models
```

**Status**: RESOLVED

---

# Audit: django__django-16662

## FAIL_TO_PASS
- `test_sorted_imports` (#24155 - Tests ordering of imports): **PASS** ✓

## PASS_TO_PASS regressions
None. All 52 tests passed.

## Pre-existing failures (not counted, confirmed against base capture)
None.

## Verdict
All FAIL_TO_PASS tests pass, zero PASS_TO_PASS regressions. The fix correctly sorts imports by type (`import` before `from`), then alphabetically by module name within each group.

**Status**: RESOLVED
