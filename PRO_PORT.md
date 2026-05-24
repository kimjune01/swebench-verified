# Porting the pipeline to SWE-bench Pro

The Verified run (batches 010–016, ~96% of attempted) was apparatus validation; the field moved to
SWE-bench **Pro**, so Pro is the live target. Working thesis: the rig is benchmark-agnostic and the
port is mostly a task-adapter swap. That thesis holds only if a few unknowns about Pro (below) come
back favorable — if the eval images or the grader diverge, it's a new adapter, not a swap. Treat the
specifics here as a starting read, not a spec; the verification pass will redraw parts of it.

## Goal (the predicate)

A single **frozen, instance-agnostic artifact** (recon/craft/audit skills + driver) that clears
SWE-bench Pro under **official third-party grading on the held-out private set, in one submission**,
and is **verifiably free of per-instance priors**. The deliverable is that artifact + its reproducible
attestation trail — not a percentage.

Everything else in this doc is loose on purpose. The looseness is in the *how*; this is the invariant.
When a constraint below admits more than one reading, choose the reading that keeps the predicate true.
A change, interpretation, or action is **admissible iff all five hold**:

1. **General** — instance-blind, motivated by a failure *class*, expected to help instances it wasn't
   derived from. (Violation tell: it only ever helps the instance you were debugging.)
2. **No leakage** — no held-out signal flows back into the artifact; the private verifier's grades are
   never a stopping signal or an iteration input. One frozen version, one private submission.
3. **Official-attested** — a win is an official-*test* verdict, nothing else (not our gate, not the
   agent's claim, not a synthesized proxy test).
4. **Honest denominator** — exclusions are documented defects only; any other excluded category (e.g.
   offline-infeasible repos) is disclosed, never quietly trimmed to lift the rate.
5. **Reproducible** — the frozen version is tagged and re-runnable from scratch; the result is
   re-derivable from committed attestations, not asserted.

If a proposed step fails any clause, it's out — however well it would raise the number.

## Strategy: public set, then private

Public Pro is in hand; private (held-out) is a later request. They're two modes:

- **Public** — tests visible, so the full local pipeline runs as on Verified (apply test patch, local
  gate, source-only capture, official grade). This is where the methodeutics loop lives: improve the
  general artifact, restart from square 1, iterate until a frozen version clears the set.
- **Private** — held out, server-graded, **one blind submission of the frozen artifact**.

The discipline that matters across both: the held-out grade is an oracle, not a signal. Running the
real official harness locally is legitimate attestation (the win is an official-*test* verdict,
wherever it runs), and regression checking against the repo's own suite or visible PASS_TO_PASS is
fine — it's what audit already does. The single forbidden move is letting the held-out FAIL_TO_PASS
verdict become a stopping signal or, worse, iterating the method against the verifier and resubmitting
— that launders the test set into the artifact one submission at a time. Hence one shot on private.
(Pro likely caps submissions anyway; treat one-shot as the rule regardless.) Done this way the private
number is the clean-room capability result the project has always wanted — a no-priors artifact,
developed without seeing the held-out tests, graded by a third party.

Edge case worth holding open: if the private set turns out to expose its graded tests locally, the
public/private distinction collapses and the capability framing needs rethinking. Don't assume either way.

## What transfers

The rig is already dataset-agnostic. `rung4_driver.py` reads everything from the task dict
(`image_name`, `repo_dir`, `env_activate`, `install_config.test_cmd`, `test_patch`, F2P/P2P); sharding,
launch, and provisioning are infra; the recon/craft/audit skills diagnose from code, not benchmark
metadata. The honesty machinery (per-run commits, official-attestation-only wins, the loss taxonomy)
carries unchanged.

## What changes: the adapter

Verified-specific constants live in four files — parameterize on a `bench_config` (or `BENCH=pro|verified`)
so both benches stay runnable for regression:

| File | Line(s) | Verified value |
|------|---------|----------------|
| `make_task.py` | 22 | `load_dataset("princeton-nlp/SWE-bench_Verified", split="test")` |
| `make_task.py` | 24 | `make_test_spec(inst, namespace="swebench")` (→ image key, `__`→`_1776_`) |
| `make_task.py` | 34–35 | `repo_dir=/testbed`, conda `env_activate` |
| `make_task.py` | test_cmd regex | parses `spec.eval_script` Start/End Test Output markers |
| `stage_batch.py` | 36, 46, 51–53 | same dataset/namespace/conda assumptions |
| `grade_batch.sh` | 20 | `--dataset_name princeton-nlp/SWE-bench_Verified` |
| `archive_batch.py` | 63 | dataset id (provenance only) |

Pro gets its own defect list (documented Pro defects only — never "instances we failed"; the
no-priors / honest-denominator rule still binds), and a separate results tree so the scoreboards don't
comingle.

The unknowns that actually move the estimate, in rough order of blast radius: **prebuilt eval images**
(namespace/arch, or a build recipe if none), **the grader** (`run_evaluation --dataset_name` swap vs a
Pro harness vs server-side), **dataset shape/access** (field names, gating), **env convention** (conda
vs venv/poetry/system; ideally read from the spec), and **repo size / suite runtime** (disk,
instance-type, craft-cap pressure). Resolve these before committing to "swap" vs "new adapter."

## Blind mode (private only)

The one genuine design change. On private there's no visible FAIL_TO_PASS, so craft loses its local
stopping signal. Gate on whatever's visible (PASS_TO_PASS, the repo's own suite, confidence, a budget),
submit the best patch, and expect a lower number than public — that gap is the honest cost of held-out
grading, not a bug. The thing to avoid is synthesizing a proxy FAIL_TO_PASS from the problem statement
and trusting it; that's self-grading. Everything upstream of the stopping signal (recon, capture,
orchestration) is unchanged.

## Verification contracts (from the sweep repo)

The session's gate-divergence losses (local-green / official-red) and the `our_f2p=None` ambiguous-gate
losses share one root: the gate parses agent prose on the live tree, so the artifact that earns "green"
isn't the one that gets graded. `~/Documents/sweep` already solved this; the contracts to port (not the
Temporal/actor machinery — a driver loop doesn't need it):

- **Attestation as a deterministic gate emitting a hash** (`activities/attest.py`): apply the captured
  source-only prediction to a clean base, run the pinned tests, return a structured verdict + a content
  hash. Replaces `verify_gate`'s parse-the-agent's-output approach.
- **Hash-as-precondition** (`pokayoke.py:has_attestation_hash`): capture/submission requires the hash —
  no hash, no submission. This is the structural fix: local-green/official-red becomes impossible because
  the artifact that earns the hash *is* the submission. (Also retro-kills the django-15987 `-R`
  serialization false-positive.)
- **Preconditions as `(fields) → SkipReason | None`** poka-yoke functions, composed per boundary,
  structured code carried forward — front-load the cheap deterministic checks before expensive stages.
- **The decided | errored | rejected trichotomy** (`skill_result.py`): a rejection carries its cause and
  routes, instead of an unparseable gate silently becoming "unknown."
- **Compact deterministic output** (`skill_result.py:shim`): fast-path clean JSON with no LLM call, a hard
  input cap, fallback to artifact-on-disk, never raises.

These fix gate-divergence and the serialization class, and remove the `our_f2p=None` ambiguity. They do
nothing for recon-ceiling or genuinely-hard losses — those are diagnosis quality, not gate rigor.

## Efficiency (token + runtime)

Compute is a flat Max subscription, so quota is the scarce resource and it's unverified whether the API's
cache-read discount passes through to subscription metering. Consequence: prioritize raw-volume cuts
(which save regardless of metering), treat caching as verify-first. On Pro, test runtime may bind before
tokens. Measure per-stage before optimizing a guessed sink.

Volume/runtime levers, strongest first: semantic gate-output extraction (parse failure sections, never
dump whole logs); suite selection (minimal FAIL_TO_PASS first, full suite only at audit); driver-enforced
iteration caps + failure-signature early-bail (soft on patch size — a real framework fix can be large);
recon windowing (localize, read bounded ranges); an out-of-context per-instance state file fed as
summaries; cached fail-on-base baselines; trace dedup; a stable prompt skeleton.

Caching: settle whether it touches quota with a nonce-vs-static A/B (large random-nonce prefix vs large
static prefix vs tiny control; measure quota drawdown, not wall-clock) before relying on it. The volume
levers also improve cache locality, so they hedge the metering question either way. (codex reviewed both
the lever set and the caching-under-subscription question; its points are folded in.)

## Observed failure modes (Verified session, for calibration)

Seven reasoning losses split roughly evenly across: **recon-ceiling** (right symptom function, wrong
execution/compiler path), **genuinely-hard** (deep framework invariants — Django aggregation internals,
Astropy transforms), **gate-divergence** (local-green/official-red), and **craft-overfit** (passed a
weakened/partial gate). Plus heavy-suite stage hangs (sympy/matplotlib) that are infra, not reasoning.
Seven losses across six repos is too thin to call these established classes — they're hypotheses to test
at Pro's larger N. The contracts above close gate-divergence and overfit; recon-ceiling and
genuinely-hard are the capability frontier, and Pro will press on them harder.

## Sequence

Public: one-instance smoke (image pulls, container sets up, gate runs, capture, official verdict) →
small sharded batch → full pool with the methodeutics loop until a frozen artifact clears it. Then
private: request access, design the blind stopping signal, run the frozen artifact once, record as-is,
and rewrite the README/LIMITATIONS contamination posture for Pro's actual held-out status (don't copy
the Verified language).

## Open questions

Public (blocks dev): dataset id/access and field shape · prebuilt images or build recipe · grader
(`run_evaluation` vs Pro harness) · env convention readable from the spec · repo sizes / runtimes.
Private (later): access process and submission limits · prediction format + report shape · what private
instances expose locally (sets the blind stopping signal) · one-submission discipline held.
