#!/usr/bin/env python3
"""Stage a batch task file: seeded random selection from SWE-bench Verified,
minus KNOWN_BAD, minus already-done (results/), minus offline-unfriendly repos.

Usage: python driver/stage_batch.py <out.json> <n> [seed]
  e.g. python driver/stage_batch.py tasks/batch_005.json 30 5

Builds the same per-instance task shape as make_task.py. The exclusion set is
the union of KNOWN_BAD.md's minimum-safe list, the instance ids already under
results/, and the sphinx-doc repo (tox-based, excluded for offline-infra reasons
per LIMITATIONS.md).
"""
import json, sys, re, random, pathlib
from datasets import load_dataset
from swebench.harness.test_spec.test_spec import make_test_spec

ROOT = pathlib.Path(__file__).resolve().parent.parent
out = sys.argv[1]
n = int(sys.argv[2])
seed = int(sys.argv[3]) if len(sys.argv) > 3 else 5

# Minimum-safe exclusion list from KNOWN_BAD.md (gold-fails, flaky, external, weak coverage, P2P regressions).
KNOWN_BAD = {
    "astropy__astropy-7166","astropy__astropy-7336","astropy__astropy-7606","astropy__astropy-7671",
    "astropy__astropy-8707","astropy__astropy-8872","django__django-10097","django__django-13710",
    "django__django-13933","django__django-15278","matplotlib__matplotlib-20488","matplotlib__matplotlib-23987",
    "matplotlib__matplotlib-24334","mwaskom__seaborn-3010","psf__requests-1724","psf__requests-1766",
    "psf__requests-1921","psf__requests-1963","psf__requests-2317","psf__requests-2674",
    "pylint-dev__pylint-6528","pylint-dev__pylint-7080","pylint-dev__pylint-7277",
    "sphinx-doc__sphinx-10323","sphinx-doc__sphinx-10435","sympy__sympy-13146","sympy__sympy-13177",
    "sympy__sympy-20590",
}
done = {p.name for p in (ROOT/"results").iterdir() if p.is_dir()}
exclude = KNOWN_BAD | done

ds = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")
pool = [r for r in ds
        if r["instance_id"] not in exclude
        and not r["instance_id"].startswith("sphinx-doc__")]  # tox, offline-unfriendly

random.seed(seed)
picks = random.sample(pool, n)

def build(inst):
    iid = inst["instance_id"]
    spec = make_test_spec(inst, namespace="swebench")
    m = re.search(r">>>>> Start Test Output'\n(.*?)\n: '>>>>> End Test Output", spec.eval_script, re.S)
    test_cmd = m.group(1).strip() if m else "python -m pytest -rA"
    return {
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

tasks = [build(i) for i in picks]
json.dump(tasks, open(out, "w"), indent=1)

from collections import Counter
repos = Counter(t["instance_id"].rsplit("-", 1)[0] for t in tasks)
print(f"wrote {out}: {len(tasks)} instances (seed={seed}, pool={len(pool)}, excluded={len(exclude)})")
for r, c in sorted(repos.items()):
    print(f"  {c:2d}  {r}")
