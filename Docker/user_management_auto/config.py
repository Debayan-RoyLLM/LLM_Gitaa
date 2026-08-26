#!/usr/bin/env python3
"""user_management_auto.config — shared configuration dict + disk persistence."""

import json
import os

CONFIG_PATH = os.environ.get("USER_MANAGEMENT_AUTO_CONFIG", "/data/.user_management_auto.json")

CONFIG = {
    "litellm_url": os.environ.get("LITELLM_URL", "http://100.102.25.115:4000"),
    "master_key": os.environ.get("LITELLM_MASTER_KEY", "internal-key"),
    "model_name": os.environ.get("MODEL_NAME", "qwen27b"),
    "cost_per_token": 0.0000001,
    # Hosts are the docker-compose service NAMES (postgres/redis), not
    # 127.0.0.1 — the console runs in its own container and the DB/cache
    # are reachable only via the compose network. Override for bare-metal
    # (non-docker) deployments via POSTGRES_HOST / REDIS_HOST.
    "postgres_host": os.environ.get("POSTGRES_HOST", "postgres"),
    "redis_host": os.environ.get("REDIS_HOST", "redis"),
    "postgres_port": 5432,
    "redis_port": 6379,
}


def load_config():
    try:
        with open(CONFIG_PATH) as fh:
            saved = json.load(fh)
        for key in CONFIG:
            if key in saved:
                CONFIG[key] = saved[key]
    except (OSError, ValueError):
        pass


def save_config():
    try:
        with open(CONFIG_PATH, "w") as fh:
            json.dump(CONFIG, fh, indent=2)
        os.chmod(CONFIG_PATH, 0o600)
    except OSError:
        pass
