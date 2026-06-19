#!/usr/bin/env python3

import yaml
import subprocess
import os
import sys
import time
import logging
from datetime import datetime


# ─── Logger ──────────────────────────────────────────────────────
log_file = f"start_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger(__name__)


# ─── Config ──────────────────────────────────────────────────────
CONFIG_FILE = os.environ.get("CONFIG_FILE", "./litellm_config.yaml")

# required
MODEL_NAME = os.environ.get("MODEL_NAME")
MODEL_PATH = os.environ.get("MODEL_PATH")
GPU_INDEX  = os.environ.get("GPU_INDEX")

# optional
VLLM_PORT     = os.environ.get("VLLM_PORT")
MAX_MODEL_LEN = os.environ.get("MAX_MODEL_LEN", "8192")
GPU_MEMORY    = os.environ.get("GPU_MEMORY",    "0.80")
DTYPE         = os.environ.get("DTYPE",         "bfloat16")


# ─── Validate required env vars ──────────────────────────────────
def validate_env():
    missing = [k for k, v in {"MODEL_NAME": MODEL_NAME,
                               "MODEL_PATH": MODEL_PATH,
                               "GPU_INDEX" : GPU_INDEX}.items() if not v]
    if missing:
        logger.error(f"Missing required env vars: {missing}")
        logger.error("Usage: MODEL_NAME=qwen-2.5-coder-7b MODEL_PATH=./models/Qwen GPU_INDEX=0 nohup python3 start_model.py &")
        sys.exit(1)

    if not os.path.isdir(MODEL_PATH):
        logger.error(f"MODEL_PATH does not exist: {MODEL_PATH}")
        sys.exit(1)


# ─── Load default port from config ───────────────────────────────
def get_vllm_port():
    if VLLM_PORT:
        return VLLM_PORT

    with open(CONFIG_FILE) as f:
        config = yaml.safe_load(f)

    for entry in config.get("model_list", []):
        if entry["model_name"] == MODEL_NAME:
            api_base = entry["litellm_params"].get("api_base", "")
            return api_base.rstrip("/").split(":")[-1].replace("/v1", "")

    logger.error(f"Model '{MODEL_NAME}' not found in {CONFIG_FILE}")
    sys.exit(1)


# ─── Kill existing vLLM ──────────────────────────────────────────
def kill_existing_vllm():
    result = subprocess.run(["pkill", "-f", "vllm serve"], capture_output=True)
    if result.returncode == 0:
        logger.info("Killed existing vLLM process")
        time.sleep(2)


# ─── Start vLLM ──────────────────────────────────────────────────
def start_vllm(port):
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = GPU_INDEX
    cmd = [
        "vllm", "serve", MODEL_PATH,
        "--port"                  , port,
        "--api-key"               , "not-needed",
        "--enforce-eager",
        "--max-model-len"         , MAX_MODEL_LEN,
        "--dtype"                 , DTYPE,
        "--gpu-memory-utilization", GPU_MEMORY,
        "--served-model-name"     , MODEL_NAME,
        "--enable-auto-tool-choice",   
        "--tool-call-parser", "hermes",

    logger.info(f"Starting vLLM | model={MODEL_NAME} port={port} gpu={GPU_INDEX}")
    logger.info(f"Command: {' '.join(cmd)}")

    return subprocess.Popen(cmd, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, bufsize=1)


# ─── Stream vLLM logs ────────────────────────────────────────────
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


# ─── Main ─────────────────────────────────────────────────────────
def main():
    logger.info(f"Log: {log_file}")
    validate_env()
    port = get_vllm_port()
    kill_existing_vllm()
    process = start_vllm(port)
    stream_logs(process)


if __name__ == "__main__":
    main()
