# Monitoring a batch run

A `launch_generic.sh` batch runs unattended for 30-60 min. Without a live watch,
a silent failure (e.g. the batch_005 regression: 30/30 zero-byte patches) only
shows at the end — an hour and real box-hours wasted. So stream a monitor that
surfaces trouble mid-flight.

Poll two sources every 60s, **emit only on change**:
- **launch log** `/tmp/launch_<prefix>.log` — all per-box driver stdout/stderr:
  stage lines, the `EMPTY patch` warning, tracebacks, terminal `ALL SHARDS DONE`.
- **per-box ledgers** `/tmp/swebench-abduction/rung4_results_<prefix>_*.jsonl` —
  one JSON line per stage; `"stage": "done"` = instance complete.

Track `done`/`empty`/`err` across iterations; print only on a delta or terminal.

The monitor runs in the user's shell (**zsh**), which — unlike bash — does **not**
expand a glob stored in a variable when used unquoted. So `LED='…b_*.jsonl'; grep … $LED`
matches nothing and silently counts 0 (this blinded the batch_005 monitor end to
end). Pipe `cat <literal-glob>` instead, so zsh expands the glob on the command line:

```bash
LOG=/tmp/launch_b2.log; LG='/tmp/swebench-abduction/rung4_results_b_*.jsonl'
pd=-1; pe=0; perr=0
while true; do
  done=$(cat $~LG 2>/dev/null | grep -c '"stage": "done"'); done=${done:-0}
  empty=$(cat $~LG 2>/dev/null | grep -c 'EMPTY patch'); empty=${empty:-0}
  err=$(grep -cE "Traceback|Killed|OOM|Connection refused|Permission denied" "$LOG" 2>/dev/null); err=${err:-0}
  [ "$empty" -gt "$pe" ] && { echo "!! EMPTY ($empty):"; cat $~LG 2>/dev/null | grep 'EMPTY patch' | tail -n +$((pe+1)); pe=$empty; }
  [ "$err" -gt "$perr" ] && { echo "!! ERRORS:"; grep -E "Traceback|Killed|OOM|Connection refused|Permission denied" "$LOG" | tail -3; perr=$err; }
  [ "$done" -ne "$pd" ] && { echo "progress $(date +%H:%M): done=$done/30 empty=$empty err=$err"; pd=$done; }
  grep -q "ALL SHARDS DONE" "$LOG" 2>/dev/null && { echo "TERMINAL: done=$done/30 empty=$empty err=$err"; break; }
  sleep 60
done
```

`$~LG` forces zsh to glob-expand the variable; under bash, plain `$LG` works too.
Run under the `Monitor` tool (each line = one notification), 60-min timeout; it
self-exits on `ALL SHARDS DONE`. **Before arming, sanity-check the counter prints
non-zero once instances finish** — a silently-zero counter is worse than none.

**Principles:** (1) *Emit on change, not on a tick* — volume scales with events,
not time; a quiet run is quiet. (2) *Silence ≠ success* — the alternation covers
crash signatures, not just `done`; ask "if a box crashed now, would this emit?".
(3) *Monitor is early warning, not the gate* — the authoritative check is the
`wc -c` sweep + official grade. (4) *Two sources cross-check* — ledger (`done`)
vs log (`EMPTY`); a bug in one path still shows in the other. (5) *Line-buffer*
any `tail -f | grep` variant (`grep --line-buffered`) or events stall in the pipe.

**After the run:** sweep for zero-byte patches before trusting the batch, then
grade + archive.

```bash
for t in $(python3 -c "import json;[print(x['instance_id'].replace('/','_')) for x in json.load(open('tasks/batch_NNN.json'))]"); do
  printf "%8s  %s\n" "$(wc -c </tmp/swebench-abduction/r4_patch_$t.diff 2>/dev/null||echo NA)" "$t"; done | sort -n | head
```
