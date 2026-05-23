# Work log

## 2026-05-22 — pipeline rebuild + first Verified run

**Skills reworked** (canonical copies in `~/Documents/june.kim/skills`, hardlinked here):
- Split the monolithic `/investigate` skill into three composable bench skills: recon (read-only diagnosis), craft (implementation), audit (verification).
- recon: single diagnostician. Correction comes from the audit -> recon outer loop (the deterministic gate is the adversary), not a parallel blind diagnosis.
- craft: generate -> filter -> arbitrate. Claude drafts the patch, a codex subagent challenges it (always: before the first gate run and on every gate failure), the gate is the final word. codex cannot reach the offline container, so craft bridges it (pulls source via the box helper, pastes into the codex prompt).
- audit: classifies failures against a captured fail-on-base baseline (no `git stash`, which could strand the patch before capture), emits a verdict and an outer-loop re-entry route.

**Driver** (`driver/rung4_driver.py`): orchestrates recon -> craft -> audit with an outer loop (max 3), routing non-RESOLVED audits back to recon (wrong diagnosis) or craft (regression), with a fixed-point halt. Adapted for SWE-bench Verified conventions: repo at `/testbed`, conda `testbed` activation in the box/gate helpers, official `_1776_` image naming. Backward-compatible with the rebench task shape.

**First Verified run: `pallets__flask-5014`** ("require a non-empty Blueprint name").
- Verdict (our gate): RESOLVED on the first pass, no outer loop. recon 96s, craft 133s, audit 46s.
- Patch: 3-line guard in `src/flask/blueprints.py` (`if name == "": raise ValueError(...)`).
- codex volley verified against codex's own session log (not the agent's narration): codex flagged that `if not name` is broader than the failing case and would pre-empt the existing `TypeError` path, recommending `if name == ""`. The agent folded it in. codex also gave one false catch ("missing a regression test"), correctly ignored since the harness applies the test separately.
- Box: EC2 m7i.xlarge, us-west-2, 90-min self-terminating watchdog. Torn down after the run.
- Caught and fixed during the run: the eval image is `swebench/sweb.eval.x86_64.pallets_1776_flask-5014` (the `__` -> `_1776_` substitution under the `swebench` namespace), not the literal double-underscore form.

Official grading of flask-5014: `run_evaluation` reports resolved (committed under `results/pallets__flask-5014/<run>/official_eval/`).

## 2026-05-22 — batch_001 (15 instances, 5 boxes parallel)

15 Verified instances, filtered against `KNOWN_BAD.md` (the filter caught 4 bad picks: astropy-7606/-7166/-7671 gold-patch-fails + requests-2317 flaky/external), pytest-based, sharded 3-per-box across 5 EC2 boxes.

- **Official: 15/15 RESOLVED.** Per-run commits with official reports + harness test logs.
- **Outer loop exercised + audit false-negative found.** `psf__requests-2931`: audit flagged a P2P regression, re-entered craft narrow-mode at depths 1 and 2, halted on budget → NOT_RESOLVED on our gate. Official grader resolves it. Audit misclassified a flaky/pre-existing P2P as a regression; the captured patch was correct. Our gate 14/15, official 15/15 — the gap is the value of the third-party grader.
- **Routing fix applied:** the driver now escalates a regression that survives one narrow attempt to `recon` (re-diagnose) instead of grinding `craft`. A no-progress guard, not a budget increase (`MAX_OUTER` stays 3: try → narrow once → re-diagnose once). Audit skill documents the harness-enforced escalation.
- **Open follow-up:** tighten audit's flaky/pre-existing P2P detection so it stops emitting false-negative regressions (the routing escalation reduces wasted compute but doesn't fix the misclassification itself).

## 2026-05-23 — batch_002 closed + non-pytest validated + batch_003 staged

- **batch_002 official: 14/15** (1 craft timeout, `xarray-6599`, no patch). Two driver `verify_gate` false-negatives overturned by the official grader (`astropy-14369`, `pytest-5809`). Running total 30/31. All boxes torn down.
- **Non-pytest smoke validated:** `django__django-11206` (`runtests.py`) and `sympy__sympy-16766` (`bin/test`) both produced patches the agents drove from raw non-pytest gate output, and both **officially graded RESOLVED**. The pipeline is not pytest-bound.
- **`verify_gate` hardened:** returns `None` (unknown) on non-pytest output instead of a misleading `False` (the field is advisory; the official grader is authoritative).
- **batch_003 staged:** random, difficulty-stratified (seed=3), drawn across all repos minus KNOWN_BAD/done/sphinx(tox). Came back representative of Verified's true distribution: 11 Django, 2 sympy, 2 matplotlib (13/15 non-pytest). This is the first batch whose rate would actually estimate something — expect it below the easy batches.

**Not yet done** (see `LIMITATIONS.md`): the clean-room ablation that would isolate the method; a larger random sample beyond 15; sphinx/tox repos (excluded for offline-infra reasons).

## 2026-05-23 — django-15987 root-caused: our-gate false-POSITIVE was patch-serialization contamination

`batch_004` logged `django__django-15987` as an our-gate false-positive (our gate RESOLVED, official UNRESOLVED) and kept it as a loss. Forensics show it was **not a real fix failure** — the fix was genuinely present and passing in-container. The divergence was entirely in how we serialized the submitted prediction.

- **Attestation, both halves present:** our gate `passing_tests_our_gate.txt` = `Ran 58 tests ... OK (skipped=1)` (F2P passes in-container); official `report.json` = `resolved: False`, F2P `settings.FIXTURE_DIRS cannot contain a default fixtures directory` fails. `patch_successfully_applied: True` is the trap — git apply "succeeded" by reversing.
- **Mechanism (from `official_eval/run_instance.log`):** the captured prediction carried two contaminants — (1) a `delete tp.patch` hunk (our scaffolding file `tp.patch` was committed into `tsha` by `git add -A` because it lived inside `{root}`), and (2) an incidental whitespace edit to the test file. Applying that mixed patch on the official's clean base tripped git's `-R` heuristic (`Reversed (or previously applied) patch detected! Assuming -R.`), which **reversed the real `loaddata.py` fix**. No fix → F2P fails.
- **Driver fix (official harness untouched):**
  - `setup`: stage the test patch at `/tmp/tp.patch`, not `{root}/tp.patch`, so `git add -A` can't sweep scaffolding into the tree.
  - `capture_patch`: emit a **source-only** prediction — `git diff {tsha} -- . ':(exclude)<testfile>'` for each `+++ b/` path in the test_patch. The official harness owns the tests; the prediction must not touch them. Matches SWE-bench's model_patch convention.
  - Either fix alone prevents this instance; together they close the false-positive class.
- **General lesson:** an our-gate-green / official-red split is not always a real loss — check `official_eval/applied_model_patch.diff` and `run_instance.log` for a `-R` reversal before recording it. Our gate runs the agent's live tree; the official grader round-trips the *serialized* patch, so contamination only surfaces there.
- **Not yet done:** re-run django-15987 through the patched driver to produce a clean re-grade attestation (expected RESOLVED). batch_004 scoreboard still records the original loss until that re-run lands.
