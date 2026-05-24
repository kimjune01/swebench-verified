# Porting the pipeline to SWE-bench Pro

Status: **planning / not started.** The Verified run (batches 010-015, 392/406) is now apparatus
validation, not the deliverable — the field moved to SWE-bench **Pro**. This doc is the port
checklist: what transfers, what must be verified about Pro before estimating effort, and the
concrete file-by-file changes once the unknowns are resolved.

The thesis is that the rig is benchmark-agnostic and a Pro run is mostly a **task-adapter swap**,
not a rebuild. That thesis is **unproven until the Step 0 unknowns below are checked** — several of
them (held-out test split, prebuilt eval images, non-conda envs) could turn a small edit into real work.

---

## Step 0 — VERIFY before touching code (these gate everything)

The pipeline makes five assumptions that are true for Verified and **may not hold for Pro**. Resolve
each before estimating effort; the answers decide whether this is a half-day adapter or a new harness.

1. **Dataset access + shape.** Where does Pro live (HF dataset id? Scale-hosted? gated/EULA?), and
   does each instance still carry `instance_id`, `problem_statement`, `test_patch`, `FAIL_TO_PASS`,
   `PASS_TO_PASS`, plus a way to derive the image and test command? If the field names differ, the
   adapter in `make_task.py` / `stage_batch.py` changes shape, not just constants.
2. **Test split visibility.** Pro is marketed as harder / more contamination-resistant. **If the
   FAIL_TO_PASS/PASS_TO_PASS or the test patch are held out** (not in the public split), our whole
   model — "apply the test patch, run the gate locally, capture a source-only patch" — breaks, and
   grading must go through whatever submission endpoint Pro provides. *This is the single highest-risk
   unknown.*
3. **Prebuilt eval images.** Verified gives us `swebench/sweb.eval.x86_64.<key>:latest` on Docker Hub
   (the `make_test_spec(namespace="swebench")` path). Does Pro publish prebuilt per-instance images?
   Under what namespace/arch? **If not**, we either build images from a Pro `make_test_spec` equivalent
   (slow, needs the build recipe) or the box setup changes substantially.
4. **Official grader.** Does `swebench.harness.run_evaluation` support Pro (a `--dataset_name` swap),
   or does Pro ship its own harness / require server-side grading? Our entire "official attestation =
   the only win" discipline depends on having a runnable authoritative grader.
5. **Env setup convention.** Verified containers are conda (`source /opt/miniconda3/bin/activate
   testbed`) with the repo at `/testbed`. Pro repos (reportedly larger / commercial) may use venv,
   poetry, system Python, or a different repo path. This is per-instance metadata, so ideally it comes
   from the spec — but verify it's *available* to read.

If 2, 3, or 4 come back unfavorable, reframe scope before proceeding — it's a new adapter, not a swap.

---

## What transfers unchanged (the rig)

These need **no changes** — they're benchmark-agnostic and were hardened this session:

- `driver/rung4_driver.py` — recon→craft→audit orchestration, outer loop, offline-container handling,
  source-only patch capture. Reads everything it needs from the task dict (`image_name`, `repo_dir`,
  `env_activate`, `install_config.test_cmd`, `test_patch`, F2P/P2P). **It is already dataset-agnostic.**
- `driver/shard_batch.py` — sharding + heavy-repo isolation (extend the `HEAVY` set if Pro has its own
  multi-GB repos; otherwise unchanged).
- `driver/launch_generic.sh`, `driver/provision_box.sh` — parallel launch + EC2 provisioning. Infra,
  not benchmark. (Pro's larger repos may need a bigger instance type / disk — see Risks.)
- Monitoring (`driver/MONITORING.md` pattern), teardown, the worklog/scoreboard/archive *workflow*.
- The honesty machinery: per-run commits, official-attestation-only wins, the loss taxonomy.

The skill text (recon/craft/audit) is task-agnostic — it diagnoses from code, not from benchmark
metadata — so the skills should not need Pro-specific edits.

---

## File-by-file changes (the adapter swap, assuming Step 0 is favorable)

All Verified-specific constants live in four files. Parameterize them on a `DATASET` /
`NAMESPACE` rather than hardcoding Pro, so the repo can run either bench:

| File | Line(s) | Verified value | Change |
|------|---------|----------------|--------|
| `driver/make_task.py` | 22 | `load_dataset("princeton-nlp/SWE-bench_Verified", split="test")` | Pro dataset id + split (or Pro loader) |
| `driver/make_task.py` | 24 | `make_test_spec(inst, namespace="swebench")` | Pro `make_test_spec` equiv + namespace, **or** a Pro-specific spec builder if the harness differs |
| `driver/make_task.py` | 34-35 | `repo_dir=/testbed`, conda `env_activate` | read from Pro spec if available; else map per Pro convention |
| `driver/make_task.py` | (test_cmd regex) | parses `spec.eval_script` Start/End markers | confirm Pro's eval script uses the same markers; else new extractor |
| `driver/stage_batch.py` | 36, 46, 51-53 | same dataset/namespace/conda assumptions | mirror the make_task changes |
| `driver/grade_batch.sh` | 20 | `--dataset_name princeton-nlp/SWE-bench_Verified` | Pro dataset name, **or** swap to Pro's grader entirely |
| `driver/archive_batch.py` | 63 | `"dataset":"princeton-nlp/SWE-bench_Verified"` | Pro dataset id (provenance only — cosmetic) |

Cleanest implementation: a single `driver/bench_config.py` (or env var `BENCH=pro|verified`) that the
four files import, so there's one switch and the Verified path stays runnable for regression checks.

Also:
- **`KNOWN_BAD.md` is Verified-specific** (defects sourced from SWE-bench issues + UTBoost). Pro needs
  its **own** defect list — start empty, populate only from documented Pro defects, never from "instances
  we failed" (the no-priors / honest-denominator rule from [project_swebench_methodeutics_goal] still binds).
- **`results/` and `SCOREBOARD.md`** — keep Pro runs in a separate tree (e.g. `results-pro/`) or tag the
  run id, so the Verified and Pro scoreboards don't comingle.

---

## Risk areas / likely divergences

- **Held-out tests (highest risk).** If Pro doesn't expose F2P/P2P or the test patch, the local-gate +
  source-only-capture model is dead and we submit predictions to a Pro endpoint for grading. Re-architect
  the audit/capture path; the recon/craft loop can still run but loses its local stopping signal.
- **No prebuilt images.** Building per-instance images is slow and needs the build recipe; budget box
  time and disk (Verified's 50GB gp3 may be tight for larger Pro repos — bump `provision_box.sh`).
- **Bigger repos / slower suites.** Expect more craft-DNF pressure; the duration-aware sharding lever
  (see WORKLOG `/retro`) becomes more valuable, and the 3600s craft cap may need revisiting.
- **Grader differences.** If Pro grades server-side, "official attestation" means their report, not a
  local `run_evaluation` — adjust `archive_batch.py`'s `official_resolved()` to parse Pro's report shape.
- **Contamination posture (the upside).** If Pro is genuinely held-out / post-cutoff, the same pipeline
  there gets closer to a *capability* claim instead of Verified's "leaderboard, contaminated" disclaimer.
  Update the README top-of-file disclaimer and `LIMITATIONS.md` to state Pro's actual contamination
  status — don't copy the Verified language blindly.

---

## Suggested sequence

1. **Step 0 verification** (above) — answer the five unknowns. Stop and re-scope if 2/3/4 are bad.
2. **One-instance smoke** — `make_task.py` on a single Pro instance, run `rung4_driver.py` on one box,
   confirm: image pulls, container sets up, gate runs, patch captures, official grader returns a verdict.
   This validates the whole adapter on one instance before any batch (mirrors how Verified started with
   `pallets__flask-5014`).
3. **Small batch** (5-10, sharded) — shake out heavy-repo isolation and grading at parallel scale.
4. **Full eligible pool** with the established batch loop, watchdog discipline, and per-run commits.
5. Update README (contamination posture, denominator), open a fresh `WORKLOG.md` section for Pro.

---

## Open questions to answer first (copy for the verification pass)

- [ ] Pro dataset id / access (HF? gated? EULA?) and per-instance field shape
- [ ] Are F2P/P2P + test_patch public, or held out?
- [ ] Prebuilt eval images? namespace/arch? else build recipe?
- [ ] Does `swebench.harness.run_evaluation` support Pro, or is there a Pro grader / submission flow?
- [ ] Env convention (conda vs venv/poetry/system) and repo path — readable from the spec?
- [ ] Repo sizes (disk/instance-type implications) and suite runtimes (craft-cap implications)
