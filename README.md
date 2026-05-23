# swebench-verified

A three-stage agent pipeline for SWE-bench Verified, built to be re-run and inspected by skeptics. The point of this repo is not the score. It is that you can clone it, run the exact procedure on the exact skills, and check the artifacts against your own grading.

## What it is

Three skills, run as separate `claude --print` invocations, chained by a driver:

- **recon** (read-only): reproduce the failing test, localize the root cause, emit a structured handoff. Single diagnostician.
- **craft** (implementation): draft the patch from the handoff, have a **codex** subagent challenge it (codex generates nothing; it filters), apply, and loop against the test gate until the FAIL_TO_PASS tests pass.
- **audit** (verification): run the full suite, classify each failure against a captured fail-on-base baseline, emit a verdict (`RESOLVED` / `NOT_RESOLVED` / `PARTIAL`) and a re-entry route.

The driver wraps these in an outer loop (max 3): a non-RESOLVED audit routes back to recon (wrong diagnosis) or craft (over-broad fix that regressed something). The system under test is an offline Docker container; the only ground truth is the test gate, never the model's own say-so.

The skills in `skills/` are **hardlinks** to the canonical authoring copies, so this repo always carries the exact text in use. If you clone the repo you get real file copies.

## Honest disclaimer (read this first)

This is a **leaderboard / capability configuration, not a contamination-clean science claim.**

- It uses post-cutoff models (Claude Sonnet generates, codex GPT-5.5 filters). Their training cutoffs postdate the SWE-bench Verified instances.
- SWE-bench Verified is contaminated for *every* modern model. That is a property of the benchmark, shared by all leaderboard entries. So this is a fair entry on the same terms as everyone else, and nothing more.
- Isolating the *method* as the cause of any result requires a separate clean-room ablation (post-cutoff instances, with-vs-without the pipeline on the same model). That is not what this repo claims. This repo demonstrates that the pipeline runs end-to-end and produces a correct, gate-verified patch.

**`LIMITATIONS.md` is the full, unhedged list** of disclaimers and limitations (single instance, the outer loop is unexercised, our gate is not the official grader, model output is stochastic, codex can be wrong, hardlinks can drift, AWS/amd64-specific infra). Read it before drawing any conclusion.

**Exclusions are explicit.** `KNOWN_BAD.md` is the list of SWE-bench instances with broken Docker envs, flaky tests, gold patches that fail to grade, or weak test coverage (sourced from SWE-bench issues and the UTBoost paper). Every batch is filtered against it before running, so any reported solve rate has an honest denominator. The exclusion is committed, not hidden.

## Result so far

One instance, `pallets__flask-5014` ("require a non-empty Blueprint name"). Artifacts live under `results/pallets__flask-5014/<run-id>/`, one directory and one git commit per run.

- **Official verdict: RESOLVED.** Graded by the official `swebench.harness.run_evaluation`, not by us. See `results/.../official_eval/report.json` (`"resolved_ids": ["pallets__flask-5014"]`, ✓=1) and `official_eval/official_test_output.txt` (the harness's own test log). This is the verdict that counts; our gate below is only the agent's stopping signal.
- Patch (`results/.../patch.diff`): a 3-line guard in `src/flask/blueprints.py`. recon 90s, craft 182s, audit 50s, first pass.
- Our gate agreed independently: the driver re-ran the suite itself (`driver_f2p_pass: true`) and saved the raw output (`passing_tests_our_gate.txt`, `60 passed`). Verdict is not the agent's say-so.
- The codex volley **demonstrably fired** (not narrated by the agent). See `codex_volley_proof.txt`, verbatim from codex's own session log: codex caught that `if not name` is broader than the failing case (it would also catch `None/False/0/[]` and pre-empt the existing `TypeError` path) and recommended `if name == ""`. The agent folded it in.

### batch_001 — 15 instances, 5 boxes in parallel

A second run: 15 Verified instances (filtered against `KNOWN_BAD.md`, pytest-based, across scikit-learn / pytest / astropy / pylint / requests / seaborn), sharded 3-per-box across 5 EC2 boxes.

- **Official verdict: 15/15 RESOLVED.** Per-instance reports + the harness's own test logs are committed under each `results/<id>/<run-id>/official_eval/`. One git commit per run.
- **The outer loop fired and the official grader caught an audit error.** On `psf__requests-2931`, our internal audit flagged a PASS_TO_PASS regression and re-entered the loop (craft narrow-mode, depths 0→1→2, then budget halt), ending NOT_RESOLVED on *our* gate. The official grader resolves it: the patch was correct; audit misclassified a flaky/pre-existing P2P as a regression. Our gate said 14/15; the truth is 15/15. This is exactly why the third-party grader is the authority and our gate is not — and it is committed evidence, not a claim. (Follow-ups: a no-progress routing escalation, now in the driver, re-diagnoses instead of grinding a stuck regression; tightening audit's flaky/pre-existing detection is open.)

### batch_002 — 15 more, 5 boxes

- **Official: 14/15 RESOLVED.** The one miss (`pydata__xarray-6599`) is a craft **timeout** (3600s, no patch captured) — an honest no-solve, not a wrong answer. Recorded as unresolved.
- Two driver false-negatives the official grader overturned: `astropy-14369` (driver `verify_gate` reported `f2p=False`) and `pytest-5809` (audit emitted no parseable verdict) both graded RESOLVED. The pytest-specific `verify_gate` parser undercounts; the official harness is the truth. Two oversized patches (astropy-14598 ~104KB, -14369 ~23KB) also resolved.

**Running total: 30/31 officially RESOLVED** (flask + batch_001 + batch_002), the lone miss a timeout. But read `LIMITATIONS.md` first — these are easy-biased, non-random, pytest-only batches. The number is plumbing/capability evidence, not a solve rate. The next batch (random, difficulty-stratified, Django-heavy) is the one whose rate would mean something.

## Run it yourself

Prerequisites:
- An x86-64 Linux Docker host (the SWE-bench eval images are linux/amd64). The provided `driver/provision.sh` spins up an AWS EC2 box with a self-terminating watchdog; any amd64 Docker host works.
- `claude` CLI (Anthropic) authenticated, and `codex` CLI (OpenAI) authenticated, both on the machine that runs the driver. The models run on the driver host; the container is offline.
- Python with `swebench` and `datasets` (`pip install -r requirements.txt`).

Steps:
```bash
# 1. Build a task JSON for any Verified instance
python driver/make_task.py pallets__flask-5014 tasks/pallets__flask-5014.json

# 2. Provision an offline-capable Docker box (or point at your own)
bash driver/provision.sh          # writes /tmp/v4smoke.env (KEY, PUBIP, ...)

# 3. Run the pipeline
python driver/rung4_driver.py /tmp/v4smoke.env tasks/pallets__flask-5014.json pallets__flask-5014

# 4. Inspect: ledger, patch, hypothesis graph land in /tmp/swebench-abduction/
```

Grade the captured patch with the **official** SWE-bench harness (do not trust this repo's gate as the grader; the gate is the agent's stopping signal, the official harness is the verdict):
```bash
python -m swebench.harness.run_evaluation \
  --dataset_name princeton-nlp/SWE-bench_Verified \
  --predictions_path <patches.jsonl> --run_id check
```

See `PROCEDURE.md` for the full step-by-step and `WORKLOG.md` for the build history.

## Layout

```
skills/{recon,craft,audit}/skill.md   the three skills (hardlinked to canonical copies)
driver/rung4_driver.py                the orchestrator (recon -> craft -> audit + outer loop)
driver/make_task.py                   builds a task JSON from any Verified instance id
driver/provision.sh                   EC2 provisioning with self-terminating watchdog
driver/link_skills.sh                 re-establish the skill hardlinks after edits
tasks/                                generated task JSONs
results/<instance>/                   ledger, patch, hypothesis graph, agent logs, codex proof
```

## License

GPL-3.0 (copyleft). See `LICENSE`. If you build on the method, share back.
