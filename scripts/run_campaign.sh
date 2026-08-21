#!/bin/bash
# Run the K=10 reliability campaign, one capsule-replica at a time.
#
# Sequential by design. Running capsules concurrently would put 14 rollouts and
# 14 containers in flight at once, and rate limiting in this harness degrades
# silently -- num_retries turns throttling into retries and then into empty
# answers, which would contaminate the very dataset being collected.
#
# Replicas already on disk are skipped by the harness (skip_existing_trajectories),
# so this is safe to re-run after an interruption.

set -u
cd "$(dirname "$0")/.."
UP=/Users/daia1/Evals/BixBench-upstream
CFG=py/config/pricing_bix8.yaml
LOG=${1:-/tmp/campaign.log}

: > "$LOG"
for spec in "bix-8:0:9" "bix-49:1:9" "bix-26:1:9"; do
  cap=${spec%%:*}; rest=${spec#*:}; lo=${rest%%:*}; hi=${rest##*:}
  for k in $(seq "$lo" "$hi"); do
    echo "########## $cap replica $k ##########" | tee -a "$LOG"
    uv run --project "$UP" --python 3.13 python py/run_agent.py \
      --capsules "$cap" --replica "$k" --config "$CFG" >> "$LOG" 2>&1
    rc=$?
    if [ $rc -ne 0 ]; then
      echo "FAILED: $cap replica $k (exit $rc) - stopping campaign" | tee -a "$LOG"
      exit $rc
    fi
  done
done
echo "########## CAMPAIGN COMPLETE ##########" | tee -a "$LOG"
