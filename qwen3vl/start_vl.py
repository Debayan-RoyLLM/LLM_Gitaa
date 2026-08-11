#!/usr/bin/env python3
"""
Standalone vLLM launcher for Qwen3-VL-8B-Instruct.

Self-contained: does NOT import from or modify the 35B stack.
Unlike start_llm.py, every setting here is read from the environment —
nothing is hardcoded inside the function.

Usage:
    MODEL_PATH=models/qwen3-vl-8b-instruct GPU_INDEX=1 python3 start_vl.py

Requires: vLLM >= 0.11, transformers >= 4.57
          (arch Qwen3VLForConditionalGeneration is unknown to older builds)
"""

import json
import os
import shlex
import subprocess
import sys
import time
import logging
from datetime import datetime


# ─── Logger ──────────────────────────────────────────────────────
log_file = f"start_vl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


# ─── Config ──────────────────────────────────────────────────────
# required
MODEL_PATH = os.environ.get("MODEL_PATH")
GPU_INDEX  = os.environ.get("GPU_INDEX")

# optional — defaults tuned for a dense 8B VL model on a single 24-48 GB GPU
MODEL_NAME    = os.environ.get("MODEL_NAME",    "qwen3vl8b")
VLLM_PORT     = os.environ.get("VLLM_PORT",     "8009")
MAX_MODEL_LEN = os.environ.get("MAX_MODEL_LEN", "32768")
GPU_MEMORY    = os.environ.get("GPU_MEMORY",    "0.85")
DTYPE         = os.environ.get("DTYPE",         "bfloat16")
MAX_NUM_SEQS  = os.environ.get("MAX_NUM_SEQS",  "64")
MAX_BATCHED   = os.environ.get("MAX_NUM_BATCHED_TOKENS", "16384")

# Multimodal limits.
#   MAX_IMAGES / MAX_VIDEOS  — hard cap per request. Without this one caller
#                              can send 50 images and exhaust the context.
#   MIN_PIXELS / MAX_PIXELS  — the single biggest throughput lever. Uncapped,
#                              a 4K photo becomes tens of thousands of tokens.
#                              1280*28*28 ≈ 1M px ≈ 1280 vision tokens.
MAX_IMAGES = os.environ.get("MAX_IMAGES", "4")
MAX_VIDEOS = os.environ.get("MAX_VIDEOS", "1")
MIN_PIXELS = os.environ.get("MIN_PIXELS", str(4 * 28 * 28))
MAX_PIXELS = os.environ.get("MAX_PIXELS", str(1280 * 28 * 28))

# Optional: allow file:// paths from the client. Leave empty to accept only
# http(s) URLs and base64 data URIs (safer — no local filesystem exposure).
ALLOWED_MEDIA_PATH = os.environ.get("ALLOWED_MEDIA_PATH", "")

# Off by default: FP8 KV cache saves VRAM but VL quality is more sensitive
# to it than text-only. Set KV_CACHE_FP8=1 only if you are VRAM-bound.
KV_CACHE_FP8 = os.environ.get("KV_CACHE_FP8", "0") == "1"

# Off by default: flashinfer is a hard startup failure if the package is
# missing or the GPU is too old — it does not fall back.
USE_FLASHINFER = os.environ.get("USE_FLASHINFER", "0") == "1"

API_KEY = os.environ.get("VLLM_API_KEY", "not-needed")


# ─── Validate ────────────────────────────────────────────────────
def validate_env():
    if not MODEL_PATH:
        logger.error("Missing required env var: MODEL_PATH")
        logger.error("Usage: MODEL_PATH=models/qwen3-vl-8b-instruct GPU_INDEX=1 python3 start_vl.py")
        sys.exit(1)

    if not GPU_INDEX:
        logger.error("Missing required env var: GPU_INDEX")
        sys.exit(1)

    # A HuggingFace repo id (org/name) is allowed — only local paths are checked.
    looks_like_hf_id = "/" in MODEL_PATH and not MODEL_PATH.startswith((".", "/", "~"))
    if not looks_like_hf_id and not os.path.isdir(MODEL_PATH):
        logger.error(f"MODEL_PATH does not exist: {MODEL_PATH}")
        sys.exit(1)


# ─── Kill only THIS model's server ───────────────────────────────
def kill_existing_vllm():
    """Match on the served-model-name so the 35B on 8007 is never touched."""
    result = subprocess.run(
        ["pkill", "-f", f"--served-model-name {MODEL_NAME}"], capture_output=True
    )
    if result.returncode == 0:
        logger.info(f"Killed existing vLLM process for '{MODEL_NAME}'")
        time.sleep(2)


# ─── Build the vLLM command ──────────────────────────────────────
def build_cmd():
    cmd = [
        "vllm", "serve", MODEL_PATH,
        "--port",                   VLLM_PORT,
        "--api-key",                API_KEY,
        "--served-model-name",      MODEL_NAME,
        "--dtype",                  DTYPE,
        "--max-model-len",          MAX_MODEL_LEN,
        "--gpu-memory-utilization", GPU_MEMORY,

        # Throughput
        "--enable-prefix-caching",
        "--enable-chunked-prefill",
        "--max-num-seqs",           MAX_NUM_SEQS,
        "--max-num-batched-tokens", MAX_BATCHED,

        # Multimodal
        "--limit-mm-per-prompt",
        json.dumps({"image": int(MAX_IMAGES), "video": int(MAX_VIDEOS)}),
        "--mm-processor-kwargs",
        json.dumps({"min_pixels": int(MIN_PIXELS), "max_pixels": int(MAX_PIXELS)}),

        # Tool calling — Qwen3-VL emits Hermes-format calls, NOT the
        # qwen3_coder XML format used by the 35B coder model.
        "--enable-auto-tool-choice",
        "--tool-call-parser",       "hermes",

        # Logging
        "--uvicorn-log-level",      "warning",
        "--max-log-len",            "128",
    ]

    if ALLOWED_MEDIA_PATH:
        cmd += ["--allowed-local-media-path", ALLOWED_MEDIA_PATH]

    if KV_CACHE_FP8:
        cmd += ["--kv-cache-dtype", "fp8"]

    if USE_FLASHINFER:
        cmd += ["--attention-backend", "flashinfer"]

    # Deliberately NOT set for this model:
    #   --moe-backend        : 8B-VL is dense, there are no MoE layers
    #   --speculative-config : Qwen3-VL has no MTP heads (35B-A3B does)
    #   --reasoning-parser   : the Instruct variant emits no <think> blocks.
    #                          Add "--reasoning-parser qwen3" ONLY for the
    #                          Qwen3-VL-*-Thinking checkpoints.
    return cmd


# ─── Start ───────────────────────────────────────────────────────
def start_vllm():
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = GPU_INDEX

    cmd = build_cmd()
    logger.info(f"Starting vLLM | model={MODEL_NAME} port={VLLM_PORT} gpu={GPU_INDEX}")
    # shlex.join, not ' '.join — the JSON mm args contain spaces and quotes,
    # so a naive join logs a command that breaks when pasted into a shell.
    logger.info(f"Command: {shlex.join(cmd)}")

    return subprocess.Popen(
        cmd, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )


# ─── Stream logs ─────────────────────────────────────────────────
def stream_logs(process):
    try:
        for line in process.stdout:
            line = line.rstrip()
            if line:
                logger.info(f"[vllm] {line}")
        process.wait()
        logger.warning(f"vLLM exited with code: {process.returncode}")
    except KeyboardInterrupt:
        process.terminate()
        process.wait()
        logger.info("vLLM stopped.")


def main():
    logger.info(f"Log: {log_file}")
    validate_env()
    kill_existing_vllm()
    stream_logs(start_vllm())


if __name__ == "__main__":
    main()
