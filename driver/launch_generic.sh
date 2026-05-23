#!/bin/bash
# Run a batch from a shard plan (see shard_batch.py). One driver process per box,
# in parallel; each waits for its box's docker then runs its shard.
# Usage: launch_generic.sh <batch.json> <shard_file>
#   shard_file lines:  <box_name> <id> <id> ...   (box_name -> /tmp/<box_name>.env)
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
BATCH="$1"; SHARD="$2"
run_box() {
  local NAME="$1"; shift; local IDS="$*"
  . /tmp/${NAME}.env; local PEM=/tmp/${KEY}.pem
  for i in $(seq 36); do
    ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i "$PEM" ec2-user@$PUBIP "sudo docker info >/dev/null 2>&1" && break || sleep 5
  done
  cd "$REPO"
  python3 driver/rung4_driver.py /tmp/${NAME}.env "$BATCH" $IDS
  echo "DONE $NAME"
}
while read -r name ids; do
  [ -z "$name" ] && continue
  run_box "$name" $ids &
done < "$SHARD"
wait
echo "=== ALL SHARDS DONE ($SHARD) ==="
