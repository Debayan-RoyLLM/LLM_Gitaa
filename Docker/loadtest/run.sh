#!/usr/bin/env bash
# Load-test runner for the internal Qwen-27B stack.
# Usage:
#   ./run.sh smoke                 # 2 min, 5 users, all 3 workloads mixed
#   ./run.sh qa 20 5m              # one workload, 20 users, 5 min
#   ./run.sh summarization 40 10m
#   ./run.sh agentic 30 10m
#   ./run.sh all 20 10m            # mixed workloads
set -euo pipefail
cd "$(dirname "$0")"

PY=~/.venvs/loadtest/bin/locust
HOST=${LITELLM_URL:-http://localhost:4000}

WORKLOAD=${1:-smoke}
USERS=${2:-5}
DURATION=${3:-2m}

case "$WORKLOAD" in
  smoke) WORKLOAD=all; USERS=${2:-5}; DURATION=${3:-2m} ;;
  qa|summarization|agentic|all) ;;
  *) echo "unknown workload: $WORKLOAD (use qa|summarization|agentic|all|smoke)"; exit 1 ;;
esac

echo ">>> workload=$WORKLOAD users=$USERS run-time=$DURATION host=$HOST"
LOCUSTFILE_WORKLOAD="$WORKLOAD" "$PY" \
  -f locustfile.py --host "$HOST" \
  --users "$USERS" --spawn-rate 5 --run-time "$DURATION" --headless \
  --only-summary \
  --csv "results_${WORKLOAD}_${USERS}u_$(date +%H%M%S)"
