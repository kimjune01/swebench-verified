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

**Not yet done** (see `LIMITATIONS.md`): official `run_evaluation` grading of the captured patch; any instance that exercises the outer loop; the clean-room ablation that would isolate the method.
