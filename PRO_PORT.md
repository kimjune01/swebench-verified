# Porting the pipeline to SWE-bench Pro

Status: **planning / not started.** The Verified run (batches 010-015, 392/406) is now apparatus
validation, not the deliverable — the field moved to SWE-bench **Pro**. This doc is the port
checklist: what transfers, what must be verified about Pro before estimating effort, and the
concrete file-by-file changes once the unknowns are resolved.

The thesis is that the rig is benchmark-agnostic and a Pro run is mostly a **task-adapter swap**,
not a rebuild. That thesis is **unproven until the Step 0 unknowns below are checked** — several of
them (prebuilt eval images, non-conda envs) could turn a small edit into real work.

## Strategy: public set first, then request the private set

We have access to the **public** Pro set now; we'll **submit a request for the private (held-out)
set** after. These are two different modes, and the pipeline runs differently in each:

- **Phase A — public set (development + method iteration).** Tests are visible (F2P/P2P + test
  patch present), so the full local pipeline works exactly as on Verified: apply the test patch, run
  the gate locally, capture a source-only patch, grade with the official harness. This is where the
  **methodeutics loop runs** — improve the general artifact, restart from square 1, iterate until the
  frozen version clears the public set.
- **Phase B — private set (single blind submission).** Tests are held out and grading is server-side.
  The **per-instance solve loop still runs** — let the skills work each instance to satisfaction using
  *local* signal (visible tests, agent confidence, budget) and submit the best patch. What you **must
  not** do is run the *methodeutics meta-loop* against the verifier: "submit → read which failed →
  tweak the method → resubmit." That turns the held-out grader into a training oracle and leaks the
  test set back into the artifact one submission at a time (leaderboard overfitting). The line is the
  **source of the stopping signal**: local signal = fine; the verifier's returned grades used to
  iterate = leak. So Phase B is **one shot**: freeze the artifact that converged on the public set,
  run its per-instance loop blind, submit **once**, accept the number. (Pro likely caps submissions for
  exactly this reason — but even an aggregate-only score overfits under repeated tuning, so treat
  one-shot as the rule regardless of the limit.)

**This is a feature, not a limitation.** The private one-shot is exactly the clean-room capability
measurement the project has wanted all along (see [project_swebench_methodeutics_goal]): a frozen,
no-priors artifact, developed without ever seeing the held-out tests, graded by a third party. It
upgrades the claim from Verified's "leaderboard, contaminated, can't isolate the method" to a genuine
held-out generalization result — *provided we never leak private-set signal back into the artifact.*

### Running tests yourself is legitimate — it is not "self-grading"

A point worth pinning so a future reader doesn't mistake the local gate for cheating: **running the
real, official test harness on your own box is legitimate attestation, not self-grading.** That is
exactly what `grade_batch.sh` did all session on Verified — it runs the official
`swebench.harness.run_evaluation` locally; the verdict counts because the *tests* are the official
ones, regardless of where the harness executes. So on the public Pro set you may run the genuine
F2P/P2P yourself, fail, iterate, and re-run freely; Phase A needs no remote grader at all.

The forbidden "self-grading" is a different thing: the agent *declaring* a fix correct with no test,
or synthesizing a proxy test from the problem statement and trusting it. The rule is "an official-
*test* verdict is the only win," not "the grader must run on someone else's machine."

**The line that actually governs leakage is not "can I run the tests" — it is "are these tests the
held-out measure I am otherwise graded against."**
- **Public set:** the tests are not the held-out measure → run them yourself freely, the methodeutics
  loop is clean.
- **Private set:** "held out" *means* you can't run the graded tests yourself — you submit and they
  grade. That's the only place the one-shot / no-resubmit-on-feedback discipline bites.
- **VERIFY what the private set actually withholds.** If you can run the private graded tests locally,
  then there is no held-out measure, the public/private distinction collapses, and the clean-capability
  framing must be rethought (it would no longer be a third-party-graded generalization claim).

### Oracle vs. regression tests (what you may run on a blind instance)

"Never touch the oracle" does **not** mean "never run tests." Regression checking is allowed and is
already core to the pipeline — it's what audit does (run the suite, classify failures against the
fail-on-base baseline). The distinction:

- **The oracle** = the held-out **FAIL_TO_PASS grade** — the test(s) that define "did you fix the bug,"
  graded by the third party. On the private set you never see these and never use their verdict as a
  stopping signal. *That* is the line.
- **Regression tests** answer a different question — "did I break what already worked" — and the verdict
  comes from *you* running tests, not from the verifier. Allowed, freely.

Safe regression sources on a blind private instance, in order of preference:
1. **The repo's own existing test suite** (ships in `/testbed`, predates any test patch, is just the
   project's code — not benchmark metadata, not the grader). Always available, always clean. This is the
   same thing a developer runs before pushing.
2. **The curated PASS_TO_PASS list, if the private set exposes it** — regression scaffolding that does
   not reveal the F2P answer.

The one trap: don't let "regression test" smuggle in the held-out F2P under a different label. If the
target test stays unseen and the verifier's pass/fail never becomes craft's stopping signal, you're
clean. The instant you'd run the *graded* test to decide you're done, that's the oracle — even if you
call it a regression check.

---

## Step 0 — VERIFY before touching code (these gate everything)

The pipeline makes five assumptions that are true for Verified and **may not hold for Pro**. Resolve
each before estimating effort; the answers decide whether this is a half-day adapter or a new harness.

1. **Dataset access + shape.** Where does Pro live (HF dataset id? Scale-hosted? gated/EULA?), and
   does each instance still carry `instance_id`, `problem_statement`, `test_patch`, `FAIL_TO_PASS`,
   `PASS_TO_PASS`, plus a way to derive the image and test command? If the field names differ, the
   adapter in `make_task.py` / `stage_batch.py` changes shape, not just constants.
2. **Test split visibility — RESOLVED by strategy.** Public set has visible tests (local pipeline
   works); private set is held out + server-graded (blind submission). The open sub-question is the
   **private submission flow**: prediction format, endpoint, rate/attempt limits, and what the returned
   report looks like. Verify before Phase B; it doesn't block Phase A. The new design challenge this
   creates is craft's **stopping signal on blind instances** — see "Phase B blind mode" below.
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

If 3 or 4 come back unfavorable, reframe scope before proceeding — it's a new adapter, not a swap.
(2 is resolved by the public-then-private strategy; its residual is the submission-flow detail for Phase B.)

### Phase B blind mode — craft's missing stopping signal

On Verified and on the **public** Pro set, craft loops against a local gate (`run the F2P tests until
they pass`). On the **private** set there is no visible F2P — so craft has no local "am I done?" signal.
Options to design before Phase B (all VERIFY-dependent on what the private set exposes):
- If the private instances ship *some* visible tests (just not the graded F2P), gate on those.
- Else craft runs to a fixed budget / the agent's own confidence + the audit's regression check on
  visible PASS_TO_PASS, then submits its best patch. Weaker signal; expect a lower private number than
  public — which is the honest cost of held-out grading, not a bug.
- Do **not** synthesize a proxy F2P from the problem statement and treat passing it as a win — that's a
  self-graded signal, exactly the thing the official-attestation rule forbids.
This is the one place Phase B is a genuine design change, not a config swap. Everything else (recon,
patch capture, box orchestration) is unchanged from Phase A.

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

- **Phase B blind mode (the real design change).** Private-set grading is server-side with no local
  F2P, so craft loses its stopping signal (see "Phase B blind mode" above). Recon/capture/orchestration
  are unchanged; only craft's halt condition and the grade/submit path differ. Budget a lower private
  number than public — held-out generalization always costs something, and reporting that honestly is
  the point.
- **Leakage discipline (claim-critical).** The private one-shot is only a clean capability result if
  **no private-set signal ever flows back into the artifact** — no per-instance tuning, no re-submitting
  a tweaked version to chase the score. One frozen version, one submission. A second "improved" private
  submission voids the no-priors claim exactly like instance-special-casing does on Verified.
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

**Phase A — public set (develop + iterate):**
1. **Step 0 verification** — answer the unknowns (3/4/5 block; the private submission flow is deferred to Phase B).
2. **One-instance smoke** — `make_task.py` on a single public Pro instance, run `rung4_driver.py` on one
   box, confirm image pulls / container sets up / gate runs / patch captures / official grader returns a
   verdict (mirrors how Verified started with `pallets__flask-5014`).
3. **Small batch** (5-10, sharded) — shake out heavy-repo isolation and grading at parallel scale.
4. **Full public pool** with the established batch loop; run the methodeutics loop (general fixes only,
   restart from square 1) until a frozen artifact clears it.

**Phase B — private set (one shot):**
5. Request private-set access; verify the submission flow (format, limits, report shape).
6. Design craft's blind stopping signal (see "Phase B blind mode").
7. Run the **frozen** artifact blind on the private instances, submit **once**, record the number as-is.
8. Update README (Pro's real contamination posture, honest denominator), keep Verified vs Pro scoreboards
   separate, open a fresh `WORKLOG.md` section for Pro.

---

## Open questions to answer first (copy for the verification pass)

**Phase A (public set) — blocks dev:**
- [ ] Public Pro dataset id / access (HF? gated? EULA?) and per-instance field shape
- [ ] Confirm public set exposes F2P/P2P + test_patch (assumed yes — that's the whole point of "public")
- [ ] Prebuilt eval images? namespace/arch? else build recipe?
- [ ] Does `swebench.harness.run_evaluation` support Pro, or is there a Pro grader?
- [ ] Env convention (conda vs venv/poetry/system) and repo path — readable from the spec?
- [ ] Repo sizes (disk/instance-type implications) and suite runtimes (craft-cap implications)

**Phase B (private set) — deferred until after public converges:**
- [ ] Private-set access/request process and any attempt/rate limits
- [ ] Submission format + endpoint, and the shape of the returned report
- [ ] What (if anything) private instances expose locally → determines craft's blind stopping signal
- [ ] Confirm one-submission discipline is honored (no score-chasing resubmits — claim-critical)
