# Hypothesis graph: scikit-learn__scikit-learn-15100

## H₀ (Abduction)
The tests fail because `strip_accents_unicode` returns strings unchanged when they are already in NFKD form, instead of filtering out combining diacritical marks.

**Evidence:**
- Test failure at line 103: `"ö"` (already NFKD: o + U+0308 combining diaresis) returned as-is instead of "o"
- Manual verification: `strip_accents_unicode("ö")` returns ['0x6f', '0x308'] instead of ['0x6f']
- Combining marks alone: `"̀́̂̃"` returned unchanged instead of empty string

## H₁ (Deduction - 99%)
**Root cause:** Early return optimization in `sklearn/feature_extraction/text.py` lines 132-137

The function contains:
```python
normalized = unicodedata.normalize('NFKD', s)
if normalized == s:
    return s  # BUG: Early return if already in NFKD form
else:
    return ''.join([c for c in normalized if not unicodedata.combining(c)])
```

**Why this is wrong:**
- Added in commit 5676ed2b4 (2016) as performance optimization
- Assumes: "if string is already NFKD, no processing needed"
- Reality: NFKD strings still contain combining characters that must be filtered out
- Example: "ö" is valid NFKD form, but still contains combining character U+0308

**Verified fix:**
Remove the early return check. Always filter combining characters:
```python
normalized = unicodedata.normalize('NFKD', s)
return ''.join([c for c in normalized if not unicodedata.combining(c)])
```

**Supporting evidence:**
- `sklearn/feature_extraction/text.py:132-137` - early return code
- Commit 5676ed2b4: "Add a check whether stripping accents is needed (#6805)"
- Manual test: fixed version passes all 5 test cases (decomposed, precomposed, combining-only, multiple marks, existing tests)
- No other code depends on the early return behavior

## Craft: Gate Loop

### Iteration 1 - Draft and Apply

**Action**: Applied the recon diagnosis — removed the early return optimization in `strip_accents_unicode` at lines 132-137.

**Change**:
```diff
--- a/sklearn/feature_extraction/text.py
+++ b/sklearn/feature_extraction/text.py
@@ -131,10 +131,7 @@ def strip_accents_unicode(s):
         ASCII equivalent.
     """
     normalized = unicodedata.normalize('NFKD', s)
-    if normalized == s:
-        return s
-    else:
-        return ''.join([c for c in normalized if not unicodedata.combining(c)])
+    return ''.join([c for c in normalized if not unicodedata.combining(c)])
```

**Codex Volley (pre-gate)**: Confirmed patch is correct. Noted performance trade-off is acceptable. The optimization was semantically wrong.

**Gate Result**: ✅ PASSED — all 107 tests pass, including `test_strip_accents`

**Resolution**: The fix removes the flawed early return that skipped combining character filtering for already-decomposed NFKD strings. The function now correctly strips accents from all inputs regardless of their initial normalization form.


## Audit: scikit-learn__scikit-learn-15100

### FAIL_TO_PASS
- `sklearn/feature_extraction/tests/test_text.py::test_strip_accents`: **PASS** ✅

### PASS_TO_PASS regressions
**None** — all 106 PASS_TO_PASS tests still pass.

### Pre-existing (not counted)
**None** — the baseline showed only `test_strip_accents` failing (AssertionError at line 103), which was the expected FAIL_TO_PASS.

4 XFAIL tests (HashingVectorizer on PyPy) are expected failures, not regressions.

### Classification
- ✅ All FAIL_TO_PASS tests now pass (1/1)
- ✅ Zero PASS_TO_PASS regressions (0/106)
- ✅ Patch is live: `sklearn/feature_extraction/text.py` modified (net -4 lines)

The fix successfully resolved the issue by removing the flawed early return optimization that prevented combining character filtering for already-decomposed NFKD strings.

