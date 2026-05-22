#!/bin/bash
# Archive one pipeline run into results/<instance>/<run_id>/ and commit it.
# One run = one commit, so git history is the per-trial record (no silent re-do).
#
# Usage: archive_run.sh <instance_id> [run_id] [official_report.json]
#   run_id defaults to a UTC timestamp.
#   official_report.json (optional): the swebench run_evaluation report to include
#   as the third-party verdict.
set -e
IID="$1"; RUNID="${2:-$(date -u +%Y%m%dT%H%M%SZ)}"; OFFICIAL="$3"
SRC="${RUN_SRC:-/tmp/swebench-abduction}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
TAG=$(echo "$IID" | tr '/' '_')
DST="$REPO/results/$IID/$RUNID"
mkdir -p "$DST"

cp "$SRC"/rung4_results_*.jsonl    "$DST/ledger.jsonl"          2>/dev/null || true
cp "$SRC/r4_patch_$TAG.diff"       "$DST/patch.diff"            2>/dev/null || true
cp "$SRC/r4_hgraph_$TAG.md"        "$DST/hypothesis_graph.md"   2>/dev/null || true
cp "$SRC/r4_failbase_$TAG.txt"     "$DST/failbase.txt"          2>/dev/null || true
cp "$SRC/r4_passgate_$TAG.txt"     "$DST/passing_tests.txt"     2>/dev/null || true
for st in recon craft audit; do
  for f in "$SRC"/r4_out_${st}_${TAG}_*.txt; do [ -e "$f" ] && cp "$f" "$DST/agent_${st}_$(basename "$f" | sed "s/.*_d/d/")"; done
done
[ -n "$OFFICIAL" ] && [ -e "$OFFICIAL" ] && cp "$OFFICIAL" "$DST/official_eval_report.json"

echo "archived run to $DST:"; ls "$DST"
git -C "$REPO" add -A
git -C "$REPO" commit -q -m "run: $IID @ $RUNID$([ -n "$OFFICIAL" ] && echo ' (official-graded)')"
echo "committed. (push is a separate, explicit step.)"
