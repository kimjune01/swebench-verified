#!/bin/bash
# Official-grade each box's shard ON that box, in parallel.
# Usage: grade_batch_generic.sh <box1> <box2> ...
grade_box() {
  local NAME="$1"
  . /tmp/${NAME}.env; local PEM=/tmp/${KEY}.pem
  local PJSON=/tmp/preds_${NAME}.json
  python3 -c "import json; ps=[json.loads(l) for l in open('/tmp/swebench-abduction/rung4_patches_${NAME}.jsonl')]; json.dump([{'instance_id':p['instance_id'],'model_name_or_path':'recon-craft-audit','model_patch':p['patch']} for p in ps], open('$PJSON','w'))"
  local IDS=$(python3 -c "import json;print(' '.join(p['instance_id'] for p in json.load(open('$PJSON'))))")
  scp -o StrictHostKeyChecking=no -i "$PEM" "$PJSON" ec2-user@$PUBIP:/tmp/preds.json >/dev/null 2>&1
  ssh -o StrictHostKeyChecking=no -i "$PEM" ec2-user@$PUBIP "
    set -e
    sudo chmod 666 /var/run/docker.sock
    command -v uv >/dev/null || (curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1)
    export PATH=\$PATH:\$HOME/.local/bin
    [ -d /tmp/sweb ] || uv venv /tmp/sweb --python 3.11 >/dev/null 2>&1
    source /tmp/sweb/bin/activate
    python -c 'import swebench' 2>/dev/null || uv pip install -q swebench >/dev/null 2>&1
    cd /tmp
    python -m swebench.harness.run_evaluation --dataset_name princeton-nlp/SWE-bench_Verified \
      --predictions_path /tmp/preds.json --run_id batch --max_workers 3 --cache_level instance \
      --instance_ids $IDS >/tmp/grade.log 2>&1
    echo GRADED_$NAME
  " 2>&1 | tail -1
  mkdir -p /tmp/grade_${NAME}
  scp -o StrictHostKeyChecking=no -i "$PEM" "ec2-user@$PUBIP:/tmp/recon-craft-audit.batch.json" /tmp/grade_${NAME}/report.json >/dev/null 2>&1
  scp -o StrictHostKeyChecking=no -i "$PEM" -r "ec2-user@$PUBIP:/tmp/logs/run_evaluation/batch/recon-craft-audit" /tmp/grade_${NAME}/instance_logs >/dev/null 2>&1
  echo "RETRIEVED $NAME"
}
for n in "$@"; do grade_box $n & done
wait
echo "=== ALL GRADED ==="
