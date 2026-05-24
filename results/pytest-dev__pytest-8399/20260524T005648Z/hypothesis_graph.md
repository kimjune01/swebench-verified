# Hypothesis graph: pytest-dev__pytest-8399
## H₀: Fixture Names Missing Underscore Prefix (abduction)

**Node ID**: H0_fixture_names_missing_underscore
**Type**: abduction
**Confidence**: 95%

### Observation
Starting with v6.2.0, unittest and nose-style xunit fixtures appear in `pytest --fixtures` output without the `-v` flag, when they should be hidden (private).

### Root Cause
Commits 50114d473 (python.py) and 489f6f449 (unittest.py) added explicit `name` parameters to xunit fixtures to fix quadratic performance issues. However, the names were not prefixed with underscore, breaking the convention that fixtures starting with `_` are private.

The pytest fixture display logic (python.py:1429 and python.py:1511) checks:
```python
if verbose <= 0 and argname.startswith("_"):
    return  # Hide private fixtures
```

Since the fixture names don't start with underscore, they're always shown.

### Evidence
- **src/_pytest/python.py:1429**: `if verbose <= 0 and argname.startswith("_"): return`
- **src/_pytest/python.py:531**: `name=f"xunit_setup_module_fixture_{self.obj.__name__}"`
- **src/_pytest/python.py:560**: `name=f"xunit_setup_function_fixture_{self.obj.__name__}"`
- **src/_pytest/python.py:812**: `name=f"xunit_setup_class_fixture_{self.obj.__qualname__}"`
- **src/_pytest/python.py:841**: `name=f"xunit_setup_method_fixture_{self.obj.__qualname__}"`
- **src/_pytest/unittest.py:147**: `name=f"unittest_{setup_name}_fixture_{obj.__qualname__}"`

### Solution
Prefix all xunit fixture names with underscore:
- `xunit_setup_module_fixture_` → `_xunit_setup_module_fixture_`
- `xunit_setup_function_fixture_` → `_xunit_setup_function_fixture_`
- `xunit_setup_class_fixture_` → `_xunit_setup_class_fixture_`
- `xunit_setup_method_fixture_` → `_xunit_setup_method_fixture_`
- `unittest_{setup_name}_fixture_` → `_unittest_{setup_name}_fixture_`

### Test Expectations
- `test_fixtures_setup_setUpClass_issue8394`: Expects unittest fixtures hidden without `-v`
- `test_fixtures_nose_setup_issue8394`: Expects nose fixtures hidden without `-v` (currently skipped due to missing nose module)


## Gate Loop 1: Implementation (craft)

**Type**: implementation
**Status**: RESOLVED ✓
**Iteration**: 1/8

### Applied Diff
```diff
--- a/src/_pytest/python.py
+++ b/src/_pytest/python.py
@@ -528,7 +528,7 @@ class Module(nodes.File, PyCollector):
             autouse=True,
             scope="module",
             # Use a unique name to speed up lookup.
-            name=f"xunit_setup_module_fixture_{self.obj.__name__}",
+            name=f"_xunit_setup_module_fixture_{self.obj.__name__}",
         )
@@ -557,7 +557,7 @@ class Module(nodes.File, PyCollector):
             autouse=True,
             scope="function",
             # Use a unique name to speed up lookup.
-            name=f"xunit_setup_function_fixture_{self.obj.__name__}",
+            name=f"_xunit_setup_function_fixture_{self.obj.__name__}",
         )
@@ -809,7 +809,7 @@ class Class(PyCollector):
             autouse=True,
             scope="class",
             # Use a unique name to speed up lookup.
-            name=f"xunit_setup_class_fixture_{self.obj.__qualname__}",
+            name=f"_xunit_setup_class_fixture_{self.obj.__qualname__}",
         )
@@ -838,7 +838,7 @@ class Class(PyCollector):
             autouse=True,
             scope="function",
             # Use a unique name to speed up lookup.
-            name=f"xunit_setup_method_fixture_{self.obj.__qualname__}",
+            name=f"_xunit_setup_method_fixture_{self.obj.__qualname__}",
         )
--- a/src/_pytest/unittest.py
+++ b/src/_pytest/unittest.py
@@ -144,7 +144,7 @@ def _make_xunit_fixture(
         scope=scope,
         autouse=True,
         # Use a unique name to speed up lookup.
-        name=f"unittest_{setup_name}_fixture_{obj.__qualname__}",
+        name=f"_unittest_{setup_name}_fixture_{obj.__qualname__}",
     )
```

### codex Pre-Gate Review
No blocking issues identified. The underscore prefix correctly aligns with pytest's fixture visibility logic (`argname.startswith("_")`). The fix preserves the performance optimization (unique names) while restoring the privacy convention. codex noted potential for test regressions if other tests assert exact fixture names, but the gate would catch those.

### Gate Result
✓ **PASSED** on first iteration

**FAIL_TO_PASS tests**: All passed
- `testing/test_unittest.py::test_fixtures_setup_setUpClass_issue8394` ✓

**Overall**: 60 passed, 30 skipped, 0 failed

### Analysis
The fix was correct on the first attempt. All 5 fixture name locations were updated to include the underscore prefix. The gate shows no regressions - all existing tests continue to pass, and the target test now passes. The hypothesis from recon was accurate: the root cause was indeed missing underscore prefixes on the explicit fixture names introduced in commits 50114d473 and 489f6f449.


## Audit: pytest-dev__pytest-8399

### Patch Status
Patch is live in container:
- `src/_pytest/python.py`: 4 fixture names prefixed with underscore
- `src/_pytest/unittest.py`: 1 fixture name prefixed with underscore

### FAIL_TO_PASS
- `testing/test_unittest.py::test_fixtures_setup_setUpClass_issue8394`: **PASSED** ✓

### PASS_TO_PASS regressions
None. All 60 tests passed.

### Pre-existing failures (not counted, confirmed against base capture)
- `test_do_cleanups_on_setup_failure.py::MyTestCase::test_one` — AssertionError in tearDown (failing on base)
- `test_do_cleanups_on_setup_failure.py::MyTestCase::test_two` — AssertionError in tearDown (failing on base)
- `test_do_cleanups_on_teardown_failure.py::MyTestCase::test_one` — AssertionError in tearDown (failing on base)
- `test_do_cleanups_on_teardown_failure.py::MyTestCase::test_two` — AssertionError in tearDown (failing on base)

### Gate Result
```
======================== 60 passed, 30 skipped in 1.68s ========================
```

### Kill report
N/A — fix is complete. The target test `test_fixtures_setup_setUpClass_issue8394` now passes. The underscore prefix causes pytest's fixture display logic (`if verbose <= 0 and argname.startswith("_"): return`) to correctly hide the xunit fixtures unless `-v` is specified. No regressions introduced.

VERDICT: RESOLVED
RE-ENTER: none
