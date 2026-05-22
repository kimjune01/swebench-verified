# Disclaimers and limitations

Read this before drawing any conclusion from this repo. The repo is built to invite scrutiny, so the limits are stated plainly rather than buried.

## Disclaimers

1. **Contaminated models (leaderboard config, not clean science).** The pipeline here runs Claude Sonnet (generator) and codex GPT-5.5 (filter). Both training cutoffs postdate the SWE-bench Verified instances. Any patch may reflect memorized solutions, not reasoning. This repo makes a *capability* claim ("the pipeline runs end-to-end and produces a gate-verified patch"), not a *method-isolation* claim.

2. **Verified is contaminated for everyone.** This is a property of the benchmark, not of our choice. Every modern leaderboard entry shares it. So this is a fair entry on the same terms, and that is all. It is not evidence that the pipeline is the cause of any result.

3. **Isolating the method needs a separate experiment.** A clean claim ("the recon/craft/audit loop is what produced the improvement") requires post-cutoff instances and a with-vs-without ablation on the same model. That experiment is **not in this repo** and has not been run.

## Limitations of the result

4. **One easy instance.** `pallets__flask-5014` is a single, small, well-specified bug. n=1 supports no statistical statement about solve rate. It is a smoke test of coordination, nothing more.

5. **The outer loop is unexercised.** Because the instance resolved on the first pass, the audit -> recon / audit -> craft re-entry, the fixed-point halt, and the narrow-on-regression mode have **never run on a real failure**. They are written but unvalidated. A failing or harder instance is needed to test them.

6. **Our gate is the agent's stopping signal; the official harness is the verdict.** The pipeline's internal `RESOLVED` is the in-container test gate, not the grader. For the committed run we **did** run the official `swebench.harness.run_evaluation` and committed its machine report (`results/.../official_eval/report.json`, resolved) plus the harness's own test log. That official report is the verdict; our gate is corroboration. A skeptic should still re-grade independently (`PROCEDURE.md`, step 4): re-runs are stochastic (limitation 7), so your patch may differ, but the procedure and grading are reproducible.

7. **Model output is stochastic.** Re-running will not reproduce the same recon text, patch wording, or codex exchange. The committed artifacts are one sample. The procedure is reproducible; the exact bytes are not.

8. **codex can be wrong, and is not the arbiter.** In the flask run codex gave one *false* catch ("the diff is missing a regression test") that is incorrect in the bench context, since the harness applies the test separately. The agent correctly ignored it. codex is a filter on the agent's draft; the gate outranks codex. Do not read a codex "looks good" as resolution.

9. **Hardlinked skills can drift.** `skills/*/skill.md` are hardlinks to the canonical authoring copies. An atomic-save editor writes a new inode and silently breaks the link, after which the repo copy and the canonical copy diverge. `driver/link_skills.sh` re-establishes the links. A clone of the repo gets a frozen real copy, not a link, so what a skeptic runs is exactly what was committed.

10. **Infra is AWS-specific and amd64-only.** `provision.sh` hardcodes an AWS region, an account-specific AMI/VPC, and an instance type. SWE-bench eval images are linux/amd64. Any amd64 Docker host works, but you will adapt the provisioning to your environment.

11. **Two model CLIs must be authenticated on the driver host.** `claude` (Anthropic) and `codex` (OpenAI). The models run on the host that runs the driver; only the system-under-test container is offline. Costs accrue on both model accounts and on the Docker host.

## Sampling bias (important for any rate)

12. **The batches are not a random sample, and they are easy-biased.** Instances are selected by *smallest test_patch* within a pytest-repo allowlist, round-robined for repo diversity. This systematically favors localized, well-specified bugs and **excludes the hard majority**: Django (`runtests`), sympy (`bin/test`), and sphinx (`tox`) are non-pytest and filtered out entirely (the driver's `verify_gate` parser is pytest-specific). So a high pass rate on these batches partly measures the selection ("we picked easy, well-scoped instances"), not the method's ceiling. A per-batch pass rate here is **not** an estimate of solve rate on Verified.

13. **The sample is tiny.** Tens of instances out of 500. Confidence intervals are wide; an all-resolved batch is consistent with a broad range of true rates. Treat the batches as plumbing/capability evidence (the pipeline runs end-to-end and yields officially-graded-correct patches across repos), not as a solve-rate measurement.

## What would make this convincing

- The clean-room ablation (limitation 3): same post-cutoff model, with vs without the pipeline, on instances after the model's cutoff.
- A run over a representative sample (limitation 4) with official grading (limitation 6).
- At least one instance that fails the first pass, to exercise and validate the outer loop (limitation 5).
