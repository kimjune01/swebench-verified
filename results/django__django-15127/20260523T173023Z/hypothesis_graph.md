# Hypothesis graph: django__django-15127

## Hypothesis H₀ (abduction, 85%)
**Root cause:** `LEVEL_TAGS` in `django/contrib/messages/storage/base.py:4` is assigned once at module import time via `LEVEL_TAGS = utils.get_level_tags()`. When `@override_settings(MESSAGE_TAGS={...})` changes the `MESSAGE_TAGS` setting, the module-level `LEVEL_TAGS` variable is not updated, causing it to retain the default tags.

**Evidence:**
- `base.py:4` - `LEVEL_TAGS = utils.get_level_tags()` executes once at import
- `base.py:41` - `level_tag` property returns `LEVEL_TAGS.get(self.level, '')` using the stale value
- Test failure shows `LEVEL_TAGS` has default values `{10: 'debug', 20: 'info', 25: 'success', 30: 'warning', 40: 'error'}` instead of overridden values
- `utils.get_level_tags()` merges `DEFAULT_TAGS` with `settings.MESSAGE_TAGS`, but is only called once

**Solution pattern:** Follow the Django standard pattern seen in `django/contrib/auth/hashers.py:104` - add a `@receiver(setting_changed)` handler that updates `LEVEL_TAGS` when `MESSAGE_TAGS` changes.

**Edit sites:**
1. `django/contrib/messages/storage/base.py` - Add imports for `setting_changed` signal and `receiver` decorator
2. `django/contrib/messages/storage/base.py` - Add receiver function after `LEVEL_TAGS` assignment to update it when `MESSAGE_TAGS` changes

## craft gate-loop iteration 1

**Hypothesis:** Add `setting_changed` signal receiver to update `LEVEL_TAGS` when `MESSAGE_TAGS` setting changes, following Django's standard pattern (e.g., `django/contrib/auth/hashers.py`).

**Implementation:**
- Added imports: `from django.core.signals import setting_changed` and `from django.dispatch import receiver`
- Added receiver function after `LEVEL_TAGS` assignment that:
  - Uses `@receiver(setting_changed, dispatch_uid='...')` decorator
  - Checks if `setting == 'MESSAGE_TAGS'`
  - Mutates `LEVEL_TAGS` in place with `clear()` + `update()` (preserves direct imports)

**codex pre-gate review:** Suggested using `clear()` + `update()` instead of rebinding to preserve direct imports, adding `dispatch_uid` to prevent duplicate receiver registration, and using explicit `setting` parameter.

**Gate result:** ✅ PASS

```
test_override_settings_level_tags (messages_tests.tests.TestLevelTags) ... ok
----------------------------------------------------------------------
Ran 2 tests in 0.000s
OK
```

**Status:** RESOLVED - FAIL_TO_PASS test passes on first iteration.

---

# Audit: django__django-15127

## FAIL_TO_PASS
- test_override_settings_level_tags (messages_tests.tests.TestLevelTags): **PASS** ✓

## PASS_TO_PASS regressions
None

## Pre-existing (not counted, confirmed against base capture)
None

## Summary
The craft patch successfully resolves the issue by adding a `setting_changed` signal handler that resets `LEVEL_TAGS` when `MESSAGE_TAGS` is modified. Both required tests pass with zero regressions.

VERDICT: RESOLVED
RE-ENTER: none
