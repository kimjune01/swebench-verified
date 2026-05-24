# Hypothesis graph: matplotlib__matplotlib-24149

## H0 (abduction, ~85%)
**When**: Initial diagnosis
**Claim**: `ax.bar` with all-NaN x positions raises `StopIteration` because `_convert_dx` doesn't catch `StopIteration` from `_safe_first_finite`.

**Evidence**:
- Stack trace shows `StopIteration` raised at `lib/matplotlib/cbook/__init__.py:1749`
- `_safe_first_finite` line 1749: `return next(val for val in obj if safe_isfinite(val))`
- When all values are non-finite, the generator yields nothing and `next()` raises `StopIteration`
- Called from `lib/matplotlib/axes/_axes.py:2182` in `_convert_dx`
- Exception handler at line 2183 catches `(TypeError, IndexError, KeyError)` but NOT `StopIteration`

**Root cause**: 
Commit cfb27b3481 (PR #23751) changed `_safe_first_non_none` → `_safe_first_finite` to skip NaN values, but didn't update all exception handlers that call it. The function now raises `StopIteration` when no finite values exist, but `_convert_dx` only catches `(TypeError, IndexError, KeyError)`.

**Edit sites**:
- `lib/matplotlib/axes/_axes.py:2183` - add `StopIteration` to exception tuple
- `lib/matplotlib/axes/_axes.py:2188` - add `StopIteration` to exception tuple

**Supporting code**:
```python
# lib/matplotlib/cbook/__init__.py:1749
return next(val for val in obj if safe_isfinite(val))  # raises StopIteration if all non-finite

# lib/matplotlib/axes/_axes.py:2181-2184
try:
    x0 = cbook._safe_first_finite(x0)
except (TypeError, IndexError, KeyError):  # Missing StopIteration!
    pass
```

**Precedent**: Other callers already catch `StopIteration`:
- `lib/matplotlib/dates.py:1864` - `except (TypeError, StopIteration)`
- `lib/matplotlib/units.py:201` - `except (TypeError, StopIteration)`

## Craft gate loop

### Iteration 1

**Hypothesis**: Add `StopIteration` to exception handlers in `_convert_dx` at lines 2183 and 2188

**Implementation**:
- Changed `except (TypeError, IndexError, KeyError):` to `except (TypeError, IndexError, KeyError, StopIteration):` at both call sites
- Matches the pattern already used in `dates.py:1864` and `units.py:201`

**codex review**: "patch is directionally correct and likely sufficient for the failing test"

**Gate result**: PASS — all 768 tests passed, including `test_bar_all_nan[png]`

**Trajectory**: Convergent (resolved)

---

# Audit: matplotlib__matplotlib-24149

## FAIL_TO_PASS
- `lib/matplotlib/tests/test_axes.py::test_bar_all_nan[png]`: **PASSED** ✓

## PASS_TO_PASS regressions
None — gate ran 768 tests with 0 failures.

Sample verification:
- `test_invisible_axes[png]`: PASSED
- `test_get_labels`: PASSED  
- `test_repr`: PASSED

## Pre-existing (not counted, confirmed against base capture)
None — no failures in patched run.

## Verdict rationale
The patch successfully resolves the issue:
- Added `StopIteration` to exception handlers at lines 2183 and 2188 in `lib/matplotlib/axes/_axes.py`
- The FAIL_TO_PASS test `test_bar_all_nan[png]` now passes
- Zero regressions introduced (768 passed, 64 skipped, 0 failed)
- Patch aligns with existing patterns in the codebase (`dates.py:1864`, `units.py:201`)

The fix is minimal, targeted, and follows established exception handling patterns for `_safe_first_finite` calls elsewhere in matplotlib.
