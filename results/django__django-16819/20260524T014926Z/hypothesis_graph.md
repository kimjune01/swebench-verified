# Hypothesis graph: django__django-16819

## H₀ (abduction, 85%)

**Failure**: test_add_remove_index expects that AddIndex followed by RemoveIndex optimizes to an empty list, but gets both operations unchanged.

**Root cause**: AddIndex class (django/db/migrations/operations/models.py:811-864) lacks a `reduce` method. The migration optimizer calls `operation.reduce(other, app_label)` on consecutive operations to determine if they can be combined/eliminated. Without a reduce method, AddIndex falls back to the base Operation.reduce() which doesn't know how to optimize with RemoveIndex.

**Evidence**:
- AddField.reduce() (fields.py:129-152) returns `[]` when followed by RemoveField for the same field — this is the working pattern
- CreateModel.reduce() (models.py:136-143) returns `[]` when followed by DeleteModel — same pattern
- AddIndex has no reduce method override, only inherits IndexOperation → Operation → base reduce (base.py:129-135) which only handles elidable operations

**Edit site**:
- django/db/migrations/operations/models.py, AddIndex class (lines 811-864): Add reduce method that checks isinstance(operation, RemoveIndex), compares model_name_lower and index.name == operation.name, returns [] if match, else super().reduce()

**Confidence**: Abduction, 85% — the pattern is clear from AddField/RemoveField, and the test directly exercises this path. No competing explanations survive.


## Craft gate loop

### Iteration 1 (gate pass)

**Change applied**: Added `reduce` method to `AddIndex` class that returns `[]` when followed by `RemoveIndex` on the same model and index name.

**Diff**:
```diff
--- a/django/db/migrations/operations/models.py
+++ b/django/db/migrations/operations/models.py
@@ -859,6 +859,15 @@ class AddIndex(IndexOperation):
     @property
     def migration_name_fragment(self):
         return "%s_%s" % (self.model_name_lower, self.index.name.lower())
+
+    def reduce(self, operation, app_label):
+        if isinstance(operation, RemoveIndex):
+            if (
+                self.model_name_lower == operation.model_name_lower
+                and self.index.name == operation.name
+            ):
+                return []
+        return super().reduce(operation, app_label)
 
 
 class RemoveIndex(IndexOperation):
```

**Gate result**: ✅ PASS
- All 39 tests pass including `test_add_remove_index`
- No regressions

**Trajectory**: Convergent-resolved (first attempt success)

**Resolution**: The recon diagnosis was correct. Adding the `reduce` method to `AddIndex` following the same pattern as `AddField.reduce()` successfully optimizes away consecutive AddIndex/RemoveIndex operations on the same index.

## Audit: django__django-16819

### Phase 1: Patch verification
```
django/db/migrations/operations/models.py | 9 +++++++++
1 file changed, 9 insertions(+)
```
Patch is live in the tree.

### Phase 2: Gate execution
Ran 39 tests in 0.010s — all PASS.

### Phase 3: Classification

**FAIL_TO_PASS**:
- test_add_remove_index: PASS ✓

**PASS_TO_PASS regressions**: none

**Pre-existing failures (not counted)**: none

### Phase 4: Verdict

All FAIL_TO_PASS tests pass, zero regressions detected.

VERDICT: RESOLVED
RE-ENTER: none
