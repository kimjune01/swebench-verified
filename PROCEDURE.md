# Procedure

The exact steps to reproduce a run. See `LIMITATIONS.md` for what a run does and does not establish.

## 0. Prerequisites

- An x86-64 Linux Docker host. SWE-bench eval images are linux/amd64. `driver/provision.sh` provisions an AWS EC2 box; any amd64 Docker host works if you adapt step 2.
- On the host that runs the driver (the "plan host", which can be your laptop):
  - `claude` CLI (the generator/orchestrator) — authenticated by **either** a Claude subscription login (`claude` logged in) **or** an Anthropic API key (`ANTHROPIC_API_KEY` in the environment). Either works.
  - `codex` CLI (the filter used by craft) — authenticated by **either** a ChatGPT subscription login **or** an OpenAI API key (`OPENAI_API_KEY`). Either works.
  - Python with `pip install -r requirements.txt` (`swebench`, `datasets`).
- The models run on the plan host. Only the system-under-test container is taken offline. The plan host needs network for the model APIs and for fetching the dataset.

Auth notes (so anyone with model access can run it):
- By default the driver passes your environment through: if `ANTHROPIC_API_KEY` is set it is used (API billing); if not, `claude` uses its logged-in subscription session.
- Set `CLAUDE_SUBSCRIPTION=1` to force the subscription path even when a key is present in your shell (drops the key for the run).
- Set `RCA_MODEL` to use a different Claude model (default `claude-sonnet-4-5`).
- The box is assumed to be AWS EC2 (`ec2-user`); set `SSH_USER` if yours differs.

## 1. Build the task JSON

```bash
python driver/make_task.py <instance_id> tasks/<instance_id>.json
# e.g.
python driver/make_task.py pallets__flask-5014 tasks/pallets__flask-5014.json
```

This pulls the instance from `princeton-nlp/SWE-bench_Verified`, derives the official image name (`swebench/sweb.eval.x86_64.<key>`, with the `__` -> `_1776_` substitution) and the exact test command from the SWE-bench eval spec, and writes the shape the driver expects.

## 2. Get an offline-capable Docker box

```bash
bash driver/provision.sh
```

Writes `/tmp/v4smoke.env` with `KEY`, `PUBIP`, `IID`, `SG`, `REGION`. The box installs Docker and sets a 90-minute self-terminating shutdown watchdog. Adapt the region/AMI/VPC/instance-type at the top of the script to your AWS account, or skip this and point the driver at your own box (the env file just needs `KEY` and `PUBIP`, and `/tmp/<KEY>.pem` must exist for SSH).

## 3. Run the pipeline

```bash
python driver/rung4_driver.py /tmp/v4smoke.env tasks/<instance_id>.json <instance_id>
```

What the driver does per instance:
1. Pull the eval image, start the container, `git apply` the test patch and commit it (so the captured `model_patch` excludes test changes).
2. Run the official test command once online to cache deps and capture the fail-on-base baseline.
3. Disconnect the container from the network (offline system under test).
4. **recon**: one read-only diagnosis, handoff to stdout, appended to the hypothesis graph.
5. **craft**: draft the patch, volley with codex, apply, loop against the gate (max 8) until FAIL_TO_PASS passes.
6. **audit**: full gate, classify against the baseline, emit `VERDICT:` and `RE-ENTER:`.
7. Outer loop (max 3): a non-RESOLVED audit re-enters recon (wrong diagnosis) or craft (regression). Halts on RESOLVED, fixed point, or budget.
8. Capture `git diff` as the model patch, tear down the container.

Outputs land in `/tmp/swebench-abduction/`:
- `rung4_results_<stem>.jsonl` (ledger), `rung4_patches_<stem>.jsonl` (patches)
- `r4_patch_<id>.diff`, `r4_hgraph_<id>.md`, `r4_failbase_<id>.txt`
- `r4_out_{recon,craft,audit}_<id>_d<n>.txt` (agent logs), `r4_prompt_*` (exact adapter prompts)

## 4. Grade with the official harness (the real verdict)

The driver's gate is the agent's stopping signal, not the grader. For the authoritative verdict, run the official SWE-bench evaluation on the captured patches:

```bash
python -m swebench.harness.run_evaluation \
  --dataset_name princeton-nlp/SWE-bench_Verified \
  --predictions_path /tmp/swebench-abduction/rung4_patches_<stem>.jsonl \
  --run_id verify --max_workers 1
```

Treat that report, not this repo's `RESOLVED`, as the verdict. (See `LIMITATIONS.md`, item 6.)

## Batch runs (multiple instances, multiple boxes)

For a batch, the tooling parallelizes across boxes and isolates heavy repos:

```bash
# 1. provision N boxes (each: docker + 180-min self-terminate watchdog)
for n in b_1 b_2 b_3 b_4 b_5; do bash driver/provision_box.sh $n & done; wait

# 2. shard the batch across boxes — heavy repos (matplotlib) get a solo box,
#    light ones pack onto the rest (avoids the batch_003 starvation bug)
python driver/shard_batch.py tasks/batch_NNN.json 5 b   # writes /tmp/b.shard

# 3. run all shards in parallel (each waits for its box's docker)
bash driver/launch_generic.sh tasks/batch_NNN.json /tmp/b.shard

# 4. official-grade each box's shard, on the box, in parallel
bash driver/grade_batch.sh b_1 b_2 b_3 b_4 b_5

# 5. archive every run as its own commit (official report included)
python driver/archive_batch.py tasks/batch_NNN.json /tmp/grade_b_
```

**Heavy-repo isolation** (`shard_batch.py`): matplotlib images are multi-GB with slow suites; co-located on a shared box they starve other instances into timeouts (observed in batch_003). The sharder gives each heavy instance its own box.

## 5. Archive into the repo

Copy the run outputs into `results/<instance_id>/` and append a `WORKLOG.md` entry. The committed `results/pallets__flask-5014/` shows the expected shape.

## Teardown

If you used `provision.sh`, terminate the box (the watchdog will anyway):
```bash
. /tmp/v4smoke.env
aws ec2 terminate-instances --instance-ids "$IID" --region "$REGION"
aws ec2 delete-security-group --group-id "$SG" --region "$REGION"
aws ec2 delete-key-pair --key-name "$KEY" --region "$REGION"
```
