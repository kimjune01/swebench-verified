#!/usr/bin/env python3
"""Derive per-instance solve time (wall-clock seconds) from the committed ledgers.

Solve time = sum of `wall_s` across the recon/craft/audit stages of a run.
For instances with more than one run dir, the resolved run is used (else the
first run). Prints percentiles and a 2-minute-bucket histogram that can be
pasted into the README's mermaid xychart-beta block.

    python driver/solve_times.py
"""
import glob
import json
import os
import statistics
from collections import Counter, defaultdict

runs = defaultdict(list)  # instance -> [(total_wall_s, official_resolved)]
for ledger in glob.glob("results/*/*/ledger.jsonl"):
    _, inst, run, _ = ledger.split("/")
    total, have_stage = 0, False
    for line in open(ledger):
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "wall_s" in d:
            total += d["wall_s"]
            have_stage = True
    if not have_stage:
        continue
    summ = os.path.join("results", inst, run, "official_eval", "summary.json")
    resolved = None
    if os.path.exists(summ):
        try:
            resolved = json.load(open(summ)).get("official_resolved")
        except (json.JSONDecodeError, OSError):
            pass
    runs[inst].append((total, resolved))

times = []
for instance_runs in runs.values():
    resolved = [t for t, ok in instance_runs if ok]
    times.append(resolved[0] if resolved else instance_runs[0][0])
times.sort()
n = len(times)


def pct(p):
    return times[min(n - 1, int(p / 100 * n))]


print(f"instances: {n}")
print(f"min {times[0]}s  p50 {pct(50)}s  p90 {pct(90)}s  "
      f"p95 {pct(95)}s  p99 {pct(99)}s  max {times[-1]}s")
print(f"mean {round(statistics.mean(times))}s")

# 20 one-minute buckets starting at 3 min (the fastest instance is ~3.1 min),
# with everything past 22 min folded into the final bar.
LO, N = 3, 20
labels = [f"{i}-{i + 1}" for i in range(LO, LO + N - 1)] + [f"{LO + N - 1}+"]
buckets = Counter()
for t in times:
    minutes = t / 60
    idx = min(N - 1, max(0, int(minutes) - LO))
    buckets[labels[idx]] += 1
print("\n1-min buckets (minutes -> count):")
for label in labels:
    print(f"{label:>5} {buckets[label]:4} {'#' * buckets[label]}")
print("\nmermaid xychart bar line:")
print("    bar [" + ", ".join(str(buckets[l]) for l in labels) + "]")
