# Monitoring a batch run

A batch launched with `launch_generic.sh` runs unattended for 30-60 min across N
boxes. Without a live watch, a silent failure (e.g. the batch_005 capture
regression that produced 30/30 zero-byte patches) isn't seen until the whole run
finishes — an hour and real box-hours wasted. The fix is a streaming monitor that
surfaces trouble *mid-flight*.

## The scheme

A poll loop that reads two sources every 60s and **emits only on change**:

- **launch log** (`/tmp/launch_<prefix>.log`) — the combined stdout/stderr of all
  per-box driver processes. Carries stage lines (`[instance] craft:`), the
  `EMPTY patch` warning, tracebacks, and the terminal `ALL SHARDS DONE`.
- **per-box ledgers** (`/tmp/swebench-abduction/rung4_results_<prefix>_*.jsonl`) —
  one JSON line per stage transition per instance. `"stage": "done"` marks an
  instance complete; `"msg": "EMPTY patch …"` marks a capture failure.

Three counters are tracked across iterations: `done` (completed instances),
`empty` (empty-patch captures), `err` (crash signatures in the log). The loop
prints a line only when one of them advances, or when the run reaches its
terminal marker. Idle periods stay silent.

```bash
LOG=/tmp/launch_b2.log; LED='/tmp/swebench-abduction/rung4_results_b_*.jsonl'
pd=-1; pe=0; perr=0
while true; do
  done=$(grep -h '"stage": "done"' $LED 2>/dev/null | wc -l | tr -d ' '); done=${done:-0}
  empty=$(grep -h 'EMPTY patch' $LED 2>/dev/null | wc -l | tr -d ' '); empty=${empty:-0}
  err=$(grep -h -c -E "Traceback|Killed|OOM|Connection refused|Permission denied" "$LOG" 2>/dev/null | tr -d ' '); err=${err:-0}
  if [ "$empty" -gt "$pe" ]; then echo "!! EMPTY PATCH ($empty):"; grep -h 'EMPTY patch' $LED 2>/dev/null | tail -n +$((pe+1)); pe=$empty; fi
  if [ "$err" -gt "$perr" ]; then echo "!! ERRORS:"; grep -h -E "Traceback|Killed|OOM|Connection refused|Permission denied" "$LOG" 2>/dev/null | tail -3; perr=$err; fi
  if [ "$done" -ne "$pd" ]; then echo "progress $(date +%H:%M): done=$done/30 empty=$empty err=$err"; pd=$done; fi
  if grep -q "ALL SHARDS DONE" "$LOG" 2>/dev/null; then echo "TERMINAL: done=$done/30 empty=$empty err=$err"; break; fi
  sleep 60
done
```

Run it under the harness `Monitor` tool (each printed line becomes a
notification) with a 60-min `timeout_ms`. It exits itself on `ALL SHARDS DONE`.

## Design principles (the part worth studying)

1. **Emit on change, not on a fixed tick.** A heartbeat every 2 min floods the
   channel and trains you to ignore it. Tracking previous counts (`pd/pe/perr`)
   and printing only on a delta means the volume of notifications scales with
   *events*, not *time*. A quiet run is quiet.

2. **Silence must not look like success.** The grep alternation covers failure
   states (`Traceback|Killed|OOM|Connection refused|Permission denied`), not just
   the happy `done` path. Ask before arming: *if a box crashed right now, would
   this emit anything?* If not, widen the alternation. A monitor that only greps
   the success marker is blind to a crashloop.

3. **The monitor is early warning, not the gate.** It tells you *when* to look,
   not *whether* the artifacts are good. The authoritative check is still a
   `wc -c` sweep over every captured patch before grading — a non-empty patch can
   still be wrong, and the monitor never claims otherwise. Two layers: fast/loose
   detection (monitor) and slow/strict verification (sweep + official grade).

4. **Two independent sources cross-check each other.** The ledger says an instance
   is `done`; the log says whether its capture was `EMPTY`. Reading both means a
   bug in one path (e.g. a driver that logs `done` but never wrote a ledger line)
   still shows up in the other.

5. **Line-buffering.** In a real pipe (`tail -f log | grep …`) pass
   `grep --line-buffered`, or events stall in the pipe buffer for minutes. The
   poll loop above re-greps whole files each tick, so it doesn't need this — but
   it's the first thing to check if a streaming variant goes quiet.

## After the run

```bash
# 1. sweep — no zero-byte patches before trusting the batch
for t in $(python3 -c "import json;[print(x['instance_id'].replace('/','_')) for x in json.load(open('tasks/batch_NNN.json'))]"); do
  printf "%8s  %s\n" "$(wc -c </tmp/swebench-abduction/r4_patch_$t.diff 2>/dev/null||echo NA)" "$t"
done | sort -n | head
# 2. grade (official harness)   3. archive (timestamped per-run commits)
```
