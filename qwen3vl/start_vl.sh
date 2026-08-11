#!/usr/bin/env bash
# Launch Qwen3-VL-8B-Instruct on its own GPU / port.
#
# GPU_INDEX=1 by default: the 35B already claims 0.80 of GPU 0. If you only
# have one GPU, set GPU_INDEX=0 AND lower gpu-memory-utilization on BOTH
# servers, or stop the 35B first.
#
#   ./start_vl.sh              # background, logs to start_vl_<ts>.log
#   FOREGROUND=1 ./start_vl.sh # run in this terminal

cd "$(dirname "$0")" || exit 1

export MODEL_NAME="${MODEL_NAME:-qwen3vl8b}"
export MODEL_PATH="${MODEL_PATH:-../models/qwen3-vl-8b-instruct}"
export GPU_INDEX="${GPU_INDEX:-1}"
export VLLM_PORT="${VLLM_PORT:-8009}"
export MAX_MODEL_LEN="${MAX_MODEL_LEN:-32768}"
export GPU_MEMORY="${GPU_MEMORY:-0.85}"

if [ "${FOREGROUND:-0}" = "1" ]; then
    exec python3 start_vl.py
else
    nohup python3 start_vl.py > /dev/null 2>&1 &
    echo "Started Qwen3-VL (pid $!) on port ${VLLM_PORT}, GPU ${GPU_INDEX}"
    echo "Tail the log:  tail -f $(dirname "$0")/start_vl_*.log"
    echo "Wait for ready: until curl -sf http://localhost:${VLLM_PORT}/health; do sleep 5; done"
fi
