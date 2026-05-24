# Hypothesis graph: sympy__sympy-16886

## H₀: Incorrect Morse mapping for digit "1" [ACTIVE]
**Type**: Deduction  
**Confidence**: 99%  
**Status**: Root cause identified

### Observation
Test `test_encode_morse` fails on assertion:
```python
assert encode_morse('12345') == '.----|..---|...--|....-|.....'
```
Actual output: `'----|..---|...--|....-|.....'` (missing leading dot)

### Trace
1. `encode_morse('12345')` called (sympy/crypto/crypto.py:1539)
2. Uses `char_morse` mapping (line 1559)
3. `char_morse` is reverse of `morse_char` (line 1536)
4. `morse_char["----"]` = "1" (line 1523) - **WRONG**
5. Should be: `morse_char[".----"]` = "1" (standard Morse code)

### Evidence
- Line 1523: `"-----": "0", "----": "1",`
- Current: digit "1" maps to `"----"` (4 dashes)
- Correct: digit "1" should map to `".----"` (1 dot + 4 dashes)
- All other digits (0, 2-9) have correct mappings
- Standard Morse pattern: digits 1-5 use increasing dots (1=`.----`, 2=`..---`, 3=`...--`, 4=`....-`, 5=`.....`)

### Root cause
Simple data error in the `morse_char` dictionary definition at line 1523.

### Edit site
- **File**: `sympy/crypto/crypto.py`  
- **Line**: 1523  
- **Change**: Replace `"----": "1"` with `".----": "1"`  
- **Impact**: Fixes both `encode_morse` (uses `char_morse`) and `decode_morse` (uses `morse_char`) since they reference the same data

### Verification
```python
$ python3 -c "from sympy.crypto.crypto import char_morse; print(char_morse['1'])"
----  # wrong
# Should output: .----
```


## Craft gate loop

### Iteration 1: Applied fix, gate GREEN
**Action**: Changed line 1523 in `sympy/crypto/crypto.py` from `"----": "1"` to `".----": "1"`

**Codex pre-gate review**: No functional problem. Fix is correct. Noted optional decode test coverage (not required for FAIL_TO_PASS).

**Gate result**: ✅ PASS — all 44 tests passed including `test_encode_morse`

**E-value trajectory**: Convergent success (green on first iteration)

**Resolution**: FAIL_TO_PASS test now passes. The minimal one-line fix corrects the Morse code mapping for digit "1" from four dashes to standard ITU Morse (one dot + four dashes), which propagates through the `char_morse` reverse mapping used by `encode_morse()`.

---

# Audit: sympy__sympy-16886

## FAIL_TO_PASS
- test_encode_morse: PASS ✓

## PASS_TO_PASS regressions
none

## Pre-existing (not counted, confirmed against base capture)
none

## Summary
The craft patch successfully fixed the `test_encode_morse` failure without introducing any regressions. All 44 tests pass.

VERDICT: RESOLVED
RE-ENTER: none
