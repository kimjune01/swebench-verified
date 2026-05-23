# Hypothesis graph: django__django-14053

## Hypothesis Node: Initial Diagnosis

**Mode**: Abduction → Deduction
**Timestamp**: Phase 1 - Baseline analysis

### H₀: Test failure observation
The test `test_post_processing` fails with:
```
AssertionError: Element counts were not equal
```
on the assertion:
```python
self.assertCountEqual(stats['post_processed'], set(stats['post_processed']))
```

This means `stats['post_processed']` contains duplicate entries - some files are being recorded as post-processed multiple times.

**Evidence**: Direct test output from gate execution.

### H₁: Root cause - Duplicate yields from post_process()

**Location**: `django/contrib/staticfiles/storage.py:203-247` (post_process method)

**Analysis**: The post_process() method has a two-phase structure:
1. **First pass** (line 231-232): Processes ALL files and yields each one
   ```python
   for name, hashed_name, processed, _ in self._post_process(paths, adjustable_paths, hashed_files):
       yield name, hashed_name, processed
   ```

2. **Subsequent passes** (line 234-239): Processes only adjustable files and yields them again
   ```python
   paths = {path: paths[path] for path in adjustable_paths}
   
   for i in range(self.max_post_process_passes):
       substitutions = False
       for name, hashed_name, processed, subst in self._post_process(paths, adjustable_paths, hashed_files):
           yield name, hashed_name, processed  # <-- Adjustable files yielded again
   ```

**Problem**: Files in `adjustable_paths` are yielded in BOTH the first pass AND the subsequent passes, causing duplicates.

**Example flow** for an adjustable CSS file:
- First pass: yields "admin/css/base.css" 
- Second pass: yields "admin/css/base.css" again
- Third pass (if substitutions continue): yields "admin/css/base.css" again

**Supporting evidence**:
- `storage.py:225-227`: Builds list of adjustable files
- `storage.py:231`: First pass processes ALL paths (including adjustable)
- `storage.py:234`: Filters to only adjustable paths
- `storage.py:238`: Subsequent passes process only adjustable paths

**Confidence**: **Deduction - 98%**
- Code path is clear and traceable
- Logic directly matches observed behavior (multiple yields → multiple entries in stats)
- Git history shows this structure was introduced in commit 53bffe8d03 (Fix #24452) to handle nested references

### Rejected hypothesis
- H₁alt: "collectstatic appends incorrectly" - REJECTED. The collect() method correctly appends each yield (line 53 of collectstatic.py). The problem is that post_process() shouldn't be yielding duplicates in the first place.


## /craft gate loop

### Gate iteration 1 (codex pre-gate review)

**Attempted fix:** Skip adjustable files in first pass only.

**Codex feedback:**
- Incomplete: adjustable files can still be yielded multiple times in the subsequent passes loop
- Need de-duplication across the whole `post_process()` generator
- Comment misleading: implies once, but loop can yield them every pass

**Action:** Revised to add global `yielded_files` set to track all yields.

### Gate iteration 2 (codex pre-gate review v2)

**Attempted fix:** Track yielded files globally and skip duplicates.

**Codex feedback:**
- Too broad: suppresses later yields even when later pass has the correct/final result
- Yields first-seen result, not final result after all processing
- Can hide errors if first pass succeeds but later pass fails
- Better shape: buffer adjustable file results and yield once after processing completes

**Action:** Adopted codex's buffering approach.

### Gate iteration 3

**Applied fix:** Buffer adjustable file results; yield non-adjustable immediately; yield buffered after loop completes.

**Gate result:** FAIL (regression in `test_post_processing_failure`)
- Target test `test_post_processing` ✓ PASS
- Regression: `test_post_processing_failure` ✗ FAIL
- Error: `AssertionError: Exception not raised`

**Codex diagnosis:**
- Buffering made adjustable-file errors non-terminal
- `_post_process()` reports failures by yielding `(name, hashed_name, exception, subst)`
- collectstatic checks if `processed` is an Exception and raises it
- Buffering delays exceptions; later passes can overwrite them with non-exception results
- collectstatic never sees the failure

**Action:** Add exception handling to yield errors immediately instead of buffering them.

### Gate iteration 4

**Applied fix:** Check `isinstance(processed, Exception)` and yield errors immediately; track failed files to exclude from further processing.

**Gate result:** ✓ GREEN - All 32 tests pass

**FAIL_TO_PASS status:**
- `test_post_processing` (post_processing behaves correctly): ✓ PASS

**PASS_TO_PASS status:**
- All 31 other tests: ✓ PASS
- Including `test_post_processing_failure`: ✓ PASS

**Resolution:** RESOLVED

## Final implementation

The fix buffers results for adjustable files (CSS files with URL references) to yield them once after multi-pass processing completes, while yielding non-adjustable files immediately in the first pass. Exception handling ensures errors are yielded immediately rather than buffered, preserving the existing failure reporting behavior.

**Changed files:**
- `django/contrib/staticfiles/storage.py` lines 224-268 (post_process method)

**Key changes:**
1. Added `processed_adjustable_files` dict to buffer adjustable file results
2. Added `failed_adjustable_files` set to track files that encountered errors
3. First pass: yield non-adjustable files immediately; buffer adjustable files; yield errors immediately
4. Subsequent passes: update buffered results; yield errors immediately
5. After loops complete: yield buffered adjustable file results once

Each file is now yielded exactly once:
- Non-adjustable files: yielded in first pass
- Adjustable files: yielded with final result after all passes complete
- Errors: yielded immediately when encountered

---

# Audit: django__django-14053

## FAIL_TO_PASS
- test_post_processing (post_processing behaves correctly): **PASS** ✓

## PASS_TO_PASS regressions
**None** - All 32 tests passed.

## Pre-existing (not counted, confirmed against base capture)
**None** - test_post_processing was failing on base, now passes. All other tests were passing on base and still pass.

## Verdict classification

**All FAIL_TO_PASS pass**: ✓ (1/1 target test passes)
**Zero PASS_TO_PASS regressions**: ✓ (all 31 PASS_TO_PASS tests still pass)

The craft patch successfully fixes the duplicate yields bug by buffering adjustable file results and yielding them once after multi-pass processing completes. Exception handling preserves the existing error reporting behavior. Full contract satisfied.

