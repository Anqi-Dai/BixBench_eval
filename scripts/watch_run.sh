#!/bin/bash
# Stream matching lines from a background run's log, then exit when the run ends.
#
# Written because `tail -f | grep` never exits: the monitor stays armed long after
# the run finishes and has to be stopped by hand. This polls the log instead,
# emits new matching lines as they appear, and returns once the watched process is
# gone -- so the monitor closes itself.
#
# BSD tail has no --pid, so the "follow until process exits" behavior is built
# from a poll loop rather than borrowed from GNU tail.
#
# Usage: scripts/watch_run.sh <logfile> <pgrep-pattern> [grep-pattern]

set -u
LOG="$1"
PROC="$2"
PAT="${3:-COST|wall clock|Traceback|Error|FAILED|Timeout occurred|docker_host|no questions matched}"

# Emit only lines added since the last poll, so nothing is repeated.
last=0
flush() {
  local n
  n=$(wc -l < "$LOG" 2>/dev/null || echo 0)
  if [ "$n" -gt "$last" ]; then
    sed -n "$((last + 1)),${n}p" "$LOG" 2>/dev/null | grep -E "$PAT"
    last=$n
  fi
}

# Give the run a moment to create its log before deciding it has already ended.
for _ in $(seq 1 10); do
  [ -f "$LOG" ] && break
  sleep 1
done

while true; do
  flush
  # Check liveness after flushing, so the final lines written just before exit
  # are still emitted on the last pass.
  if ! pgrep -f "$PROC" > /dev/null 2>&1; then
    sleep 3          # let any buffered tail of the log land
    flush
    echo "[watch_run] process '$PROC' finished; monitor closing"
    exit 0
  fi
  sleep 5
done
