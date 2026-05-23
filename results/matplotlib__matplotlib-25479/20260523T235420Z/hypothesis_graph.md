# Hypothesis graph: matplotlib__matplotlib-25479

## H₀ (abduction, 85%)
**Tests fail because Colormap.__eq__ includes name comparison and ColormapRegistry.__getitem__ doesn't update the returned colormap's name**

### Evidence
1. `test_colormap_equals` fails at line 201: Two colormaps with identical lookup tables but different names are not equal
   - Error: `assert cm_copy == cmap` fails when `cm_copy.name = "Test"` but otherwise identical
   - Source: lib/matplotlib/tests/test_colors.py:201

2. `test_set_cmap_mismatched_name` fails at line 1663: Retrieved colormap has wrong name
   - Registered with name='wrong-cmap' but cmap.name='test-cmap'
   - Retrieved colormap has name='test-cmap' instead of 'wrong-cmap'
   - Error: `assert cmap_returned.name == "wrong-cmap"` → AssertionError: 'test-cmap' != 'wrong-cmap'
   - Source: lib/matplotlib/tests/test_colors.py:1663

### Root Cause Analysis

**Problem 1: Name included in equality comparison**
- Location: `lib/matplotlib/colors.py:777`
- Code: `if (not isinstance(other, Colormap) or self.name != other.name or ...)`
- The __eq__ method returns False if names differ, even if lookup tables are identical
- Test expectation: "different names are equal if the lookup table is the same" (line 199 comment)

**Problem 2: Retrieved colormap retains original name instead of registered name**
- Location: `lib/matplotlib/cm.py:79`
- Code: `return self._cmaps[item].copy()`
- When colormap is retrieved, it returns a copy with the original name
- Registration flow:
  1. User creates colormap with name='some_cmap_name'
  2. Registers with name='my_cmap_name' via `colormaps.register(name='my_cmap_name', cmap=cmap)`
  3. Register method (line 149) stores: `self._cmaps[name] = cmap.copy()`
  4. Copy preserves original name='some_cmap_name' (colors.py:768-774 __copy__ copies __dict__)
  5. Retrieval via __getitem__ returns copy with name='some_cmap_name' instead of 'my_cmap_name'

### Confidence: 85% (abduction)
- High confidence based on direct code reading and test failure messages
- Both issues are straightforward: equality logic and name assignment
- No complex interactions or hidden state

## Craft Gate Loop

### Iteration 1 - Draft and Apply

**Volley with codex (pre-gate):**
- Showed codex the drafted patch
- codex noted: "Minimal patch is directionally right for the two failing tests. Main missing piece is auditing all registry retrieval paths and pinning alias behavior."
- Concerns raised about other access paths and alias behavior, but approved for testing

**Changes applied:**
1. `lib/matplotlib/colors.py:777` - Removed `self.name != other.name` from `__eq__` check
2. `lib/matplotlib/cm.py:79-81` - Modified `__getitem__` to set `cmap.name = item` before returning

**Gate result:**  
- ✓ test_colormap_equals PASSED
- ✓ test_set_cmap_mismatched_name PASSED
- ✗ test_double_register_builtin_cmap FAILED (pytest.warns(UserWarning) caught MatplotlibDeprecationWarning instead)

**Investigation:**
Tested if the failing test is a regression from the patch:
- Stashed changes and re-ran test_double_register_builtin_cmap
- Result: Test ALSO fails without my changes
- Conclusion: Pre-existing test failure, not a regression

**Both warnings are correctly issued:**
```
Warnings caught: 2
  - MatplotlibDeprecationWarning: The register_cmap function was deprecated...
  - UserWarning: Overwriting the cmap 'viridis' that was already in the registry.
```

The test appears to have a pytest.warns() interaction issue unrelated to this patch.

**Resolution:** Both FAIL_TO_PASS tests pass. The one failing test is pre-existing.


---

# Audit: matplotlib__matplotlib-25479

## FAIL_TO_PASS
- test_colormap_equals: PASSED ✓
- test_set_cmap_mismatched_name: PASSED ✓

## PASS_TO_PASS regressions
none

## Pre-existing (not counted, confirmed against base capture and craft stash test)
- test_double_register_builtin_cmap - FAILED with pytest.warns(UserWarning) catching MatplotlibDeprecationWarning instead
  - Confirmed pre-existing in craft iteration 1 by stashing changes and re-running test
  - Both warnings (DeprecationWarning and UserWarning) are correctly issued, but pytest.warns() interaction issue

## Kill report
N/A - All FAIL_TO_PASS tests pass and zero regressions.

VERDICT: RESOLVED
RE-ENTER: none
