# Failure attribution: a post-run investigation

A post-run learning writeup, not a scoreboard change. The run left 12 of 438 eligible instances
not-won (`SCOREBOARD.md`). Going back to classify them surfaced one thing worth recording — and it is
**not** "the gap is mostly variance" (every stochastic loop has variance; saying so is trivial). The
finding is that **the two obvious ways to attribute a not-won both point the wrong way** — toward a
capability ceiling that mostly isn't there — and that the one residue which *looks* most like
capability is a deterministic grading artifact.

Nothing below edits a committed number. `SCOREBOARD.md` stays the frozen artifact (426/438). A re-run
is a new sample, not a re-roll; conversions here are **telemetry**, and the losing runs stay in history.

## What we did

Took the 12 not-won and refused to attribute them from the logs. Ran two probes, plus a direct probe of
the one stubborn case:

- **Counterfactual** (`testify`): re-grade each *committed* source-only patch on a clean base with the
  official parser. Answers **"is this artifact correct?"**
- **Rerun**: re-run the *frozen, unchanged* loop and re-grade. Answers **"can the loop ever solve it?"**
- **Constrained blind probe** on django-14170: three independent diagnoses of the failing test, each
  told *the test file is fixed — you may not edit it.*

## What we fixed

A **source-only gate** in the active driver (`swebench-pro/driver/rung5_driver.py`):

- the iteration gate and the final `verify_gate` restore the gold test files before every run, so an
  agent edit to a test can't false-green the gate;
- craft and recon prompts state tests are gold-locked and forbid handing off a test edit as a fix;
- `_strip_test_blocks` gained a test-path-convention fallback, so the source-only *capture* still holds
  on a held-out private split where the gold test paths aren't visible.

This mirrors the invariant the official harness already enforces (it `git checkout`s test files to gold
before grading). It is **not** retrofitted into the frozen `skills/` here — the Verified artifact stays
as it ran.

## What we tried again

Reran all 12 frozen instances once each. Reran django-14170 as the three constrained blind diagnoses.

## What worked

- **11 of 12 recovered** to official `RESOLVED_FULL` on *new* shas — under the frozen loop, no change.
  (That is the rerun probe, not the fix.)
- **3 of 3 blind diagnoses** reached the gold-equivalent source-only fix, touching the two gold source
  files and no tests.
- The gate change closes the false-green hatch at the **mechanism level** — but it has **not** been run
  through the official amd64 grader yet, so no win is banked on it.

## What the attribution is

The gap is not capability. Both obvious signals bias toward a wall:

- **The log** names the gold mechanism, so it reads "almost had it." It is the least trustworthy
  signal — it is optimized to sound resolved.
- **The counterfactual** converted **0/12**, which reads as a hard capability wall.

Both mislead because they answer *is this artifact correct?*, not *can the loop ever solve it?* — and
only the second bears on capability. The rerun answers it: a single differently-sha'd success
**falsifies** the wall for an instance (a universal-negative dies to one counterexample — no sample
size needed). So 11 of 12 are demonstrably not walls. The artifact-correctness and instance-solvability
questions **diverge**; "variance" is just the label left once you stop reading the wrong probe.

The asymmetry is where care is owed: the *positive* call (solved once → not a wall) is certain at n=1;
the *negative* call (never solves → genuine wall) is the expensive universal-negative. django-14170 was
the one byte-identical failure — the best wall candidate. It isn't one. Its committed patch removed an
optimization and **edited the test file** to weaken the assertions that broke; the official grader
restores gold tests, so the change fails every time, same sha. The byte-identical-wrong-sha is the
signature of a **deterministic false-green** — a wrong *outcome* (our gate passed the agent's weakened
test) posing as a wrong *answer* (the loop "can't"). The constrained probe discharges the negative call
by mechanism, not by counting reruns: **the loop emits the correct fix once test-editing is barred.**

This false-green mechanism is the **load-bearing, contamination-immune** result — a fact about the
harness and the gate, not about model knowledge. (We do not claim the model *reasoned* the fix rather
than recalled it; the benchmark is contaminated — see `LIMITATIONS.md`. "The loop emits the fix" is the
honest ceiling.) A second-order note: the three blind diagnoses *agreeing* wasn't what mattered — each
alone escaped. The constraint, not the fan-out, broke the attractor.

The same bias turns inward, too. After adding a craft cap + capture-at-timeout, a timeout-DNF
(sympy-19040) recovered on rerun — but the cap **never fired** (craft converged well under the limit).
The recovery was variance; crediting the cap would have banked a false attribution onto our own fix.

## What we recommend

1. **Adopt the source-only gate** going forward — it makes our gate agree with the official grader by
   construction, removing the false-green class.
2. **Validate django-14170 on amd64 and confirm the mechanism fired** (a reverted test edit in the gate
   log) before crediting the fix. A pass alone is not proof the lever caused it.
3. **Earn any new number with a from-scratch single-version run** under the corrected gate — not by
   patching 12 conversions into the frozen scoreboard.
4. **Carry the de-biasing protocol:** don't attribute from logs; pick the probe that answers your actual
   question; one success refutes a wall, but asserting a wall needs a mechanism; a green outcome after a
   change is not evidence the change caused it. Cheap negatives (0/12) are the find — they told us the
   wall wasn't where the obvious signals put it.
