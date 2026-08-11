#!/usr/bin/env bash
# Stop ONLY the Qwen3-VL server. Matches on --served-model-name so the
# 35B on port 8007 and the 9B on 8008 are left running.

MODEL_NAME="${MODEL_NAME:-qwen3vl8b}"

echo "Processes matching '${MODEL_NAME}':"
pgrep -af -- "--served-model-name ${MODEL_NAME}" || { echo "  (none)"; exit 0; }

read -rp "Kill these? [y/N] " reply
[ "$reply" = "y" ] || { echo "Aborted."; exit 0; }

pkill -f -- "--served-model-name ${MODEL_NAME}"
sleep 3

if pgrep -f -- "--served-model-name ${MODEL_NAME}" > /dev/null; then
    echo "Still alive, sending SIGKILL..."
    pkill -9 -f -- "--served-model-name ${MODEL_NAME}"
fi

echo "Done. Remaining vLLM processes:"
pgrep -af "vllm serve" || echo "  (none)"
