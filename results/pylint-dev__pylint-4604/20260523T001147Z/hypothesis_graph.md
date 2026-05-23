# Hypothesis graph: pylint-dev__pylint-4604

## H₀: Test import error (2026-05-22)
**Type:** Abduction (initial observation)
**Status:** Confirmed by code inspection

The tests fail to run because `tests/checkers/unittest_variables.py` tries to import `IS_PYPY` from `pylint.constants`, but this constant does not exist in that module.

**Evidence:**
- Test file line 30: `from pylint.constants import IS_PYPY`
- `pylint/constants.py` does not define `IS_PYPY`
- Other parts of the codebase use `platform.python_implementation() == "PyPy"` for PyPy detection (see `tests/test_self.py:386`)

**Consequence:** Tests cannot be collected, so we cannot observe the actual test failures.

## H₁: Root cause - Missing Attribute node handling in type comment parsing (2026-05-22)
**Type:** Deduction (traced through code)
**Status:** Active hypothesis
**Confidence:** 95%

The `_store_type_annotation_node` method in `pylint/checkers/variables.py` fails to extract names from `Attribute` nodes in type comments.

**Code path:**
1. When pylint processes an assignment like `a = 1  # type: foo.Bar`
2. The `leave_assign` method (line 1242) calls `_store_type_annotation_names(node)`
3. Which calls `_store_type_annotation_node(node.type_annotation)` (line 1849)
4. The type_annotation is an `astroid.Attribute` node representing `foo.Bar`
5. `_store_type_annotation_node` (line 1823) only handles:
   - `astroid.Name` nodes (lines 1825-1827)
   - `astroid.Subscript` nodes (lines 1829-1843)
6. For any other node type (including `Attribute`), it returns early at line 1830
7. Therefore, the `foo` name is never added to `self._type_annotation_names`
8. Later, when checking imports (line 2034), `foo` is not in `_type_annotation_names`
9. So `import foo` is flagged as unused-import

**Supporting evidence:**
- `pylint/checkers/variables.py:1830` - Early return for non-Subscript nodes
- Tested with astroid: `# type: foo.Bar` creates an `Attribute` node
- Tested with astroid: `# type: foo.Bar[int]` creates a `Subscript` node and DOES work (because Subscript handling uses `nodes_of_class(astroid.Name)` at line 1840-1843)

**Verification:**
```python
import astroid
code = "import foo\na = 1  # type: foo.Bar"
module = astroid.parse(code)
assign = module.body[1]
print(assign.type_annotation.__class__.__name__)  # Output: Attribute
```

## Edit sites required:

1. **`pylint/constants.py`**: Add `IS_PYPY` constant definition
   - Add after line 11: `IS_PYPY = platform.python_implementation() == "PyPy"`
   - Need to import platform at top of file

2. **`pylint/checkers/variables.py:1823-1843`**: Fix `_store_type_annotation_node` method
   - Add handling for `astroid.Attribute` nodes before the Subscript check
   - When encountering an Attribute node, extract all Name nodes using `nodes_of_class(astroid.Name)`
   - This will handle `foo.Bar`, `Bar.Baz`, and nested attribute accesses


## Craft gate loop - iteration 1

**Changes applied:**
1. Added `IS_PYPY` constant to `pylint/constants.py` (imported `platform` module and defined `IS_PYPY = platform.python_implementation() == "PyPy"`)
2. Added `Attribute` node handling in `pylint/checkers/variables.py::_store_type_annotation_node` method

**Gate result:** ✅ PASS (21/21 tests passed)

All FAIL_TO_PASS tests now pass:
- test_bitbucket_issue_78 ✅
- test_no_name_in_module_skipped ✅
- test_all_elements_without_parent ✅
- test_redefined_builtin_ignored ✅
- test_redefined_builtin_custom_modules ✅
- test_redefined_builtin_modname_not_ignored ✅
- test_attribute_in_type_comment ✅ (the new test)
- All other tests ✅

**Trajectory:** Convergent-success (first gate run passes all tests)

**Resolution:** The recon diagnosis was correct. The fix handles `astroid.Attribute` nodes in type comments by extracting all `Name` nodes, just like the existing `Subscript` fallback logic.

## Audit: pylint-dev__pylint-4604 (2026-05-22)

### Phase 1: Patch confirmation
✅ Patch is live in container:
- `pylint/constants.py` now defines `IS_PYPY` at line 14
- `platform` module imported
- `pylint/checkers/variables.py` includes Attribute node handling

### Phase 2: Gate execution
Command: `/tmp/gate-pylint-dev_pylint-4604`
Result: **21 passed, 1 warning in 0.22s**

### Phase 3: Classification

#### FAIL_TO_PASS (all must pass)
All 21 tests were in FAIL_TO_PASS (baseline had collection error):
- ✅ test_bitbucket_issue_78
- ✅ test_no_name_in_module_skipped
- ✅ test_all_elements_without_parent
- ✅ test_redefined_builtin_ignored
- ✅ test_redefined_builtin_custom_modules
- ✅ test_redefined_builtin_modname_not_ignored
- ✅ test_redefined_builtin_in_function
- ✅ test_unassigned_global
- ✅ test_listcomp_in_decorator
- ✅ test_listcomp_in_ancestors
- ✅ test_return_type_annotation
- ✅ test_attribute_in_type_comment
- ✅ test_custom_callback_string
- ✅ test_redefined_builtin_modname_not_ignored (WithTearDown)
- ✅ test_redefined_builtin_in_function (WithTearDown)
- ✅ test_import_as_underscore
- ✅ test_lambda_in_classdef
- ✅ test_nested_lambda
- ✅ test_ignored_argument_names_no_message
- ✅ test_ignored_argument_names_starred_args
- ✅ test_package_all

**Result:** 21/21 PASS ✅

#### PASS_TO_PASS regressions
None (PASS_TO_PASS list was empty)

#### Pre-existing failures
None (all tests passed)

### Phase 4: Verdict

**Contract fulfilled:**
- ✅ All FAIL_TO_PASS tests now pass (21/21)
- ✅ Zero PASS_TO_PASS regressions (0/0)
- ✅ No new failures introduced

**Baseline context:**
- Base: ImportError during test collection (0 tests collected)
- Post-fix: All 21 tests collected and passed
- Root cause: Missing `IS_PYPY` constant in `pylint/constants.py`
- Fix: Added `import platform` and `IS_PYPY = platform.python_implementation() == "PyPy"`

