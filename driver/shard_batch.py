#!/usr/bin/env python3
"""Assign a batch's instances to boxes, isolating heavy repos onto their own box.

Heavy repos (multi-GB images, slow suites — matplotlib is the standout) starve
co-tenants when sharded together: in batch_003, matplotlib on a shared box
timed two other instances into empty patches. So a heavy instance gets a box to
itself; light instances pack onto the remaining boxes.

Usage: shard_batch.py <batch.json> <num_boxes> <box_prefix>
  writes /tmp/<box_prefix>.shard with lines:  <box_prefix>_<i> <id> <id> ...
"""
import json, sys
from collections import defaultdict

HEAVY = {"matplotlib"}  # repo prefix (instance_id.split("__")[0]); extend as needed

batch_file, n, prefix = sys.argv[1], int(sys.argv[2]), sys.argv[3]
ids = [b["instance_id"] for b in json.load(open(batch_file))]
heavy = [i for i in ids if i.split("__")[0] in HEAVY]
light = [i for i in ids if i.split("__")[0] not in HEAVY]

boxes = [[] for _ in range(n)]
heavy_boxes = set()
for k, i in enumerate(heavy):              # one heavy per box (round-robin if heavy > n)
    b = k % n; boxes[b].append(i); heavy_boxes.add(b)
light_targets = [b for b in range(n) if b not in heavy_boxes] or list(range(n))
for k, i in enumerate(light):              # pack light onto heavy-free boxes
    boxes[light_targets[k % len(light_targets)]].append(i)

out = f"/tmp/{prefix}.shard"
with open(out, "w") as f:
    for b in range(n):
        if boxes[b]:
            f.write(f"{prefix}_{b+1} " + " ".join(boxes[b]) + "\n")
print(f"wrote {out}")
for b in range(n):
    if boxes[b]:
        tag = " [HEAVY-solo]" if b in heavy_boxes else ""
        print(f"  {prefix}_{b+1}: {len(boxes[b])} instance(s){tag} -> {boxes[b]}")
