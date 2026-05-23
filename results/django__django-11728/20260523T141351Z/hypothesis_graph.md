# Hypothesis graph: django__django-11728

## Hypothesis H₁: Off-by-one in bracket-matching loop termination

**Type**: Deduction (95%)  
**Status**: Active root cause

### Observation

Four test cases fail in `test_simplify_regex` when regex patterns have groups (named or unnamed) that end at the final character of the pattern:

```
Pattern: r'^(?P<a>\w+)/b/(?P<c>\w+)'
Expected: '/<a>/b/<c>'
Got:      '/<a>/b/(P<c>\w+)'  <- trailing group not replaced

Pattern: r'^(?P<a>\w+)/b/(\w+)'
Expected: '/<a>/b/<var>'
Got:      '/<a>/b/(\w+)'       <- trailing group not replaced
```

### Root cause

Both `replace_named_groups()` and `replace_unnamed_groups()` in `django/contrib/admindocs/utils.py` use identical bracket-matching loops that check `if unmatched_open_brackets == 0` at the **start** of each iteration (before processing the current character).

When a group's closing `)` is the last character in the substring:
1. Loop processes the `)`, decrements `unmatched_open_brackets` to 0
2. Loop terminates (no more characters)
3. The check `if unmatched_open_brackets == 0:` never executes on the next iteration
4. Group pattern is never appended to the result list
5. Replacement never happens

**Traced execution** for pattern `r'^(?P<c>\w+)'` (simplified):
- Named group `(?P<c>` found at [1:7]
- Remaining substring: `\w+)`
- Loop: idx=0(`\`), idx=1(`w`), idx=2(`+`), idx=3(`)` → decrement to 0
- Loop ends, never checks balanced condition
- Result: group not in `group_pattern_and_name`, never replaced

**Contrasting case** that works: `r'^(?P<c>\w+)/$'`:
- Remaining substring: `\w+)/$`
- Loop: ... idx=3(`)` → decrement to 0, idx=4(`/`) → **check passes, appends**
- Result: group replaced correctly

### Evidence

`django/contrib/admindocs/utils.py`:169-186 (`replace_named_groups`):
```python
for idx, val in enumerate(pattern[end:]):
    # If brackets are balanced, the end of the string for the current
    # named capture group pattern has been reached.
    if unmatched_open_brackets == 0:  # <- CHECK BEFORE PROCESSING
        group_pattern_and_name.append((pattern[start:end + idx], group_name))
        break
    # ... process val, update unmatched_open_brackets
```

`django/contrib/admindocs/utils.py`:206-217 (`replace_unnamed_groups`):  
Identical pattern, same bug.

### Edit sites

**Both functions need the same fix**: after the loop, check if brackets became balanced on the last character.

1. `django/contrib/admindocs/utils.py` lines 169-186 (`replace_named_groups`):
   - After the `for` loop ends, add: `if unmatched_open_brackets == 0: group_pattern_and_name.append(...)` with the appropriate end index

2. `django/contrib/admindocs/utils.py` lines 206-217 (`replace_unnamed_groups`):
   - After the `for` loop ends, add: `if unmatched_open_brackets == 0: group_indices.append(...)` with the appropriate end index

**Alternatively**: Move the balanced-check to AFTER processing each character instead of before (requires refactoring the loop structure).

### Competing hypotheses

None. The bug is deterministic and directly observable in code execution trace.

### Confidence

Deduction — 95%. The execution trace proves the bug, and the fix location is unambiguous.


## Craft: Gate Loop

### Iteration 1: Initial fix after codex review

**Change**: Moved balance check to immediately after decrementing `unmatched_open_brackets` in both `replace_named_groups()` and `replace_unnamed_groups()`. Changed from checking at the start of each iteration to checking right after processing a closing `)` and decrementing the counter.

**codex feedback**: Initial draft had post-loop check that would cause duplicate appends. codex recommended moving the append to happen immediately after decrementing to 0.

**Applied changes**:
- In `replace_named_groups()`: Moved `if unmatched_open_brackets == 0:` check to immediately after `unmatched_open_brackets -= 1`, changed pattern slice to `pattern[start:end + idx + 1]` to include the final character
- In `replace_unnamed_groups()`: Same structural change, adjusted index to `start + 1 + idx + 1`

**Gate result**: ✅ PASS
- All 46 tests passed
- `test_simplify_regex` now passes for all test cases including those with trailing groups
- `test_app_not_found` passes
- No regressions

**Evidence trajectory**: Convergent (resolved)

**Status**: RESOLVED - FAIL_TO_PASS tests pass, no regressions


## Audit: django__django-11728

### Gate output
All 46 tests passed in 1.528s.

### FAIL_TO_PASS results
- `test_simplify_regex (admin_docs.test_views.AdminDocViewFunctionsTests)`: ✅ **PASS**
- `test_app_not_found (admin_docs.test_views.TestModelDetailView)`: ✅ **PASS**

### PASS_TO_PASS regressions
**None** — all 44 PASS_TO_PASS tests remain passing.

### Pre-existing failures
**None** — fail-on-base baseline showed all tests passing before the patch.

### Classification
- Both FAIL_TO_PASS tests now pass
- Zero regressions introduced
- Clean gate run

VERDICT: RESOLVED
RE-ENTER: none
