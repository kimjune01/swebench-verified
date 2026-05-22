#!/usr/bin/env python3
"""Build a driver task JSON from any SWE-bench Verified instance id.

Usage: python make_task.py <instance_id> [out.json]
  e.g. python make_task.py pallets__flask-5014 tasks/pallets__flask-5014.json

Emits the shape rung4_driver.py expects:
  instance_id, image_name, repo_dir, env_activate, test_patch,
  install_config.test_cmd, problem_statement, FAIL_TO_PASS, PASS_TO_PASS

Requires: pip install swebench datasets  (see ../requirements.txt)
The image name uses the official SWE-bench convention: namespace `swebench`,
arch x86_64, with the `__` -> `_1776_` substitution applied by the harness.
"""
import json, sys, re
from datasets import load_dataset
from swebench.harness.test_spec.test_spec import make_test_spec

iid = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else f"{iid}.json"

ds = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")
inst = next(r for r in ds if r["instance_id"] == iid)
spec = make_test_spec(inst, namespace="swebench")  # -> swebench/sweb.eval.x86_64.<key>:latest

# Pull the exact test command out of the official eval script (the line(s)
# between the Start/End Test Output markers). Falls back to a pytest default.
m = re.search(r">>>>> Start Test Output'\n(.*?)\n: '>>>>> End Test Output", spec.eval_script, re.S)
test_cmd = m.group(1).strip() if m else "python -m pytest -rA"

task = {
    "instance_id": iid,
    "image_name": f"docker.io/{spec.instance_image_key}",
    "repo_dir": "/testbed",
    "env_activate": "source /opt/miniconda3/bin/activate testbed",
    "test_patch": inst["test_patch"],
    "install_config": {"test_cmd": test_cmd},
    "problem_statement": inst["problem_statement"],
    "FAIL_TO_PASS": json.loads(inst["FAIL_TO_PASS"]),
    "PASS_TO_PASS": json.loads(inst["PASS_TO_PASS"]),
}
json.dump([task], open(out, "w"), indent=1)
print(f"wrote {out}")
print(f"  image:    {task['image_name']}")
print(f"  test_cmd: {test_cmd}")
print(f"  F2P: {len(task['FAIL_TO_PASS'])}  P2P: {len(task['PASS_TO_PASS'])}")
