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

## 2026-05-23 — batch_005 first run lost to a capture regression (self-inflicted, ~$2)

The first `capture_patch` fix used a shell-side `git diff {tsha} -- . ':(exclude)<testfile>'`. The `:(exclude)` pathspecs were single-quoted **inside** the `bash -lc '...'` single-quoted command, so the inner quotes terminated the command early and emptied the capture. batch_005's first run produced **30/30 zero-byte patches**; the agents had genuinely fixed the instances (capture_diag `--stat` showed real source edits) but serialization dropped everything, and teardown removed the containers — fixes unrecoverable.

- **Caught at the `wc -c` sweep**, before grading/committing — so no empty-patch "losses" were ever recorded. The our-gate `r4_passgate` attestations survived (they're written pre-capture) but are useless without a patch or official verdict.
- **Remediation (committed `e5c1995`):** do the test-file exclusion in Python over the full diff (`_strip_test_blocks`), not via a shell pathspec. Quoting-safe, unit-tested (source kept, test block dropped). The `git diff {tsha}` capture command is back to the known-good form.
- **Re-run** on the same live boxes (watchdogs reset to +180) with the fixed driver.
- **Lesson:** any shell-side pathspec/arg built from data and embedded in a `bash -lc '...'` wrapper is a quoting hazard — prefer post-processing in Python. And always sweep `wc -c` on captured patches before trusting a batch.
- **Cost:** ~$2 EC2 (10 boxes × ~1 box-hr); model compute $0 on the Max plan. Don't sweat it — commit the mistake, remediate, keep chugging.

## 2026-05-23 — batch_005 re-run clean (29/30 captured); craft hang on sympy-19040 (REVISIT)

Re-run with the Python-side filter: **29/30 non-empty patches**, our-gate 29/30 RESOLVED, **0 empty captures** (vs 30/30 before — fix validated). Official grading in progress.

- **`sympy__sympy-19040` DNF — craft hang.** recon finished normally (435s, good handoff); the **craft** `claude` call then ran the full 3600s wall-clock timeout without returning and was killed (`TimeoutExpired`). No patch captured → grades unresolved. Not the capture bug, not an infinite loop — the timeout did its job; it's an honest did-not-finish.
- **Suspected cause:** craft's "max 8 gate iterations" is *instructed to the agent, not driver-enforced*, so on a heavy suite (sympy) the agent can grind gate runs until the hour cap instead of stopping at 8. Also burned ~1h of API tokens (this was still on the API key, pre-zshrc fix).
- **Levers to revisit (NOT yet done):** (a) drop craft's 3600s timeout — median craft is far shorter, p90 total solve is 762s; (b) hard-count gate iterations in the driver and kill craft at 8. One instance in 106, so low urgency — flagged for `/retro`.

**Official grade (RUNID 20260523T060702Z): 29/30 resolved.** All 29 captured patches resolved officially, 0 unresolved among them, **0 `-R` reversals** — every clean source-only prediction survived the official apply. The contamination class (django-15987) is closed end-to-end. Only miss is sympy-19040 (DNF, no patch). Scoreboard now **104/106** (losses: django-15987 unfixed-rerun-pending, sympy-19040 DNF).

- **New minor finding (REVISIT):** a `__init__.py.bak` file leaked into django-13023's prediction. Harmless here — a *new* file is additive, can't trigger `-R`, and it resolved — but `capture_patch`'s `find … -name "*.bak" -delete` should have removed it pre-diff and didn't. Latent detritus risk; the find's escaped-paren form through ssh→`bash -lc` may be misfiring. Low urgency (resolved anyway), flagged for `/retro`. **Fixed (`9b431fa`):** detritus blocks (`*.bak`/pyc/caches) now dropped from the prediction in Python (`_strip_test_blocks`), quoting-safe, subtractive-only.

## 2026-05-24 — batch_006: 29/30 official (subscription billing); 2nd craft DNF

batch_006 (seed=6, 30 disjoint instances: 15 django, 7 sympy, 4 matplotlib, 2 sklearn, 1 each astropy/pytest) launched on the same boxes with **`CLAUDE_SUBSCRIPTION=1`** (the zshrc export does NOT reach the Bash-tool shell snapshot — must prefix explicitly; verified empty otherwise). RUNID 20260523T071951Z.

- **Official: 29/30 resolved**, 0 unresolved among graded, 0 `-R` reversals. Detritus fix held — no `.bak`/artifact leaks. Scoreboard now **133/136**.
- **`matplotlib__matplotlib-25311` DNF — craft hang (2nd occurrence).** recon fine (188s), craft ran the full 3600s and was killed. Identical to sympy-19040: heavy/slow suite → craft grinds gate iterations to the hour cap. **Two DNFs now share this root cause** (sympy + matplotlib), so the revisit lever is no longer a one-off.
  - **Mechanism (clarified):** the gate runs the *targeted* official test_cmd (one file, not the whole suite). For sympy the cost is the fixed `import sympy` + `bin/test -C` startup tax paid every one of craft's ~8 iterations — small tests, heavy import. matplotlib: multi-GB image + figure-render comparison tests.
  - **LEADING `/retro` lever (matches real-repo dev practice):** gate craft's inner loop on **F2P only** (1-2 tests, `pytest file::test -x`-style fast feedback), full F2P+P2P once at audit/verify. The real repo doesn't hang — a dev/CI pays the import once, not 8×; the hang is *our* loop re-running the heavy official command each iteration. Tradeoff: a P2P break is unseen until audit (caught there, costs a re-entry). Secondary levers: driver-enforced gate-iteration cap; trim craft's 3600s timeout (not blindly).

## 2026-05-24 — batch_007: 30/30 official (perfect batch, 0 DNF)

batch_007 (seed=7, 30 disjoint: 17 django, 7 sympy, 3 xarray, 2 pytest, 1 matplotlib), subscription billing, fresh boxes. RUNID 20260523T141351Z. **Official 30/30 resolved**, 30/30 captured, 0 empty, 0 `-R` reversals, 0 craft hangs. Scoreboard now **163/166**.

- **Heavy-suite craft hang is instance-specific, not category-wide.** This batch had 7 sympy + 1 matplotlib and *none* DNF'd — they finished within the 3600s budget. So the lever framing holds: the hang isn't "all sympy/matplotlib," it's specific instances whose craft loop happens to grind. Reinforces making the redo a *diagnostic* (does more time converge them, or are they stuck?) rather than blanket-tripling the timeout — most heavy instances don't need it.
- Fresh boxes meant no stale `/tmp/logs` cross-batch contamination in grade retrieval (the batch_006 double-count); tally was clean 30/30.
- Three standing losses unchanged: django-15987 (contamination, fixed-but-rerun-pending), sympy-19040 + matplotlib-25311 (craft DNFs from prior batches).

## 2026-05-24 — batch_008: 30/30 official (2nd perfect batch); 200 runs, 193/196

batch_008 (seed=8, 30 disjoint: 15 django, 7 sympy, +spread), subscription, fresh boxes. RUNID 20260523T153335Z. **Official 30/30**, 0 empty, 0 DNF (7 sympy, all converged). Scoreboard **193/196**, 200 total archived runs. Two perfect batches back-to-back (007, 008). Boxes kept alive for batch_009 (last of session). Standing 3 losses unchanged.
- Subscription billing held; tonight ~120 instances at 10-wide parallel with **no rate throttling** (Sonnet's Max ceiling is generous — informs the "full-500 on subscription" plan: dollars ~$30 EC2 / $0 model, no quota wall).

## 2026-05-24 — RESUME STATE (session paused, tokens out) — batch_009 ungraded

**Boxes ALIVE:** 10 boxes (b_1..b_10), watchdog extended to **+720min ≈ alive until ~21:35 2026-05-24**. IPs/keys in `/tmp/b_*.env`. Local bg procs (launch `bjnknqlxy`, monitor) may have died with the session — the EC2 boxes did not.

**batch_009 status (updated):** launch COMPLETED. 29/30 captured; `django__django-15957` (b_7) is a **confirmed DNF** (exhausted outer-loop attempts, no patch — 4th standing loss). **Grading launched** (bg `bv07ch181`, `/tmp/grade_b9.log`) — if it finished, just archive; if the bg proc died with the session, re-run `grade_batch.sh` then archive.

**To resume (from repo root):**
1. Check holdout: `cat /tmp/swebench-abduction/rung4_results_b_7.jsonl | grep 15957` — see if it reached `done`.
2. Sweep: `wc -c /tmp/swebench-abduction/r4_patch_*.diff` for batch_009 ids (expect 29-30 non-empty).
3. Grade: `bash driver/grade_batch.sh b_1 b_2 b_3 b_4 b_5 b_6 b_7 b_8 b_9 b_10` (fresh boxes had no stale logs at launch, but they've now graded nothing yet — tally filtered by batch_009 ids regardless).
4. Archive: `python3 driver/archive_batch.py tasks/batch_009.json /tmp/grade_b_` → per-run commits.
5. `python3 driver/scoreboard.py` then commit SCOREBOARD.md + WORKLOG.md.
6. **Tear down** (last batch of session): `for n in $(seq 1 10); do ( . /tmp/b_$n.env; aws ec2 terminate-instances --instance-ids "$IID" --region "$REGION"; ) & done; wait` — then leak-sweep.

**Scoreboard before batch_009:** 193/196 (batches 5-8 archived). 3 standing losses: django-15987, sympy-19040, matplotlib-25311. Re-runs deferred to campaign end.

## 2026-05-24 — batch_009 archived: 28/30 (first genuine reasoning loss); session close

batch_009 (seed=9, 30 disjoint: 16 django, 4 matplotlib, 4 sympy, +spread) graded + archived, RUNID 20260523T173023Z. **Official 28/30.** Scoreboard now **221/226 (~98%)**, 230 total runs. Two losses, two *different* kinds:
- `django__django-15957` — **DNF**: exhausted outer-loop attempts (audit kept catching a regression, re-diagnosed, never converged within MAX_OUTER=3). No patch. The outer loop did its job (didn't ship a regression) but ran out of budget.
- `sympy__sympy-20438` — **first genuine reasoning loss**: patch applied cleanly, graded UNRESOLVED. Not a DNF, not contamination, not capture — the fix was simply wrong. This is the honest failure class we *want* to see (the machine got the answer wrong, transparently), distinct from the infra/serialization losses.
- **5 standing losses now:** django-15987 (contamination, rerun-pending), sympy-19040 + matplotlib-25311 + django-15957 (DNFs), sympy-20438 (reasoning). 4 of 5 are sympy/matplotlib/heavy or contamination; only 1 is a clean reasoning miss.
- Boxes torn down at session close. Re-runs (django-15987 esp.) deferred to campaign end per plan.
- **Monitor (fixed zsh-safe form) worked** — counter advanced 0→29 correctly (vs the silently-zero old one); only missed the late craft timeout because it hit its own 60-min cap first.
- **Grade-retrieval gotcha (noted, not blocking):** boxes accumulate `/tmp/logs/run_evaluation/...` across gradings, so `scp -r` of instance_logs mixed batch_005 + batch_006 dirs (58 reports for 30 instances). `archive_batch.py` filters by the batch's own IDs so archiving was correct, but ad-hoc tallies must filter too.
