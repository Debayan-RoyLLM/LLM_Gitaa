#!/usr/bin/env python3
"""user_management_auto.config — shared configuration dict + disk persistence."""

import json
import os

CONFIG_PATH = os.environ.get("USER_MANAGEMENT_AUTO_CONFIG", "/data/.user_management_auto.json")

CONFIG = {
    "litellm_url": os.environ.get("LITELLM_URL", "http://100.102.25.115:4000"),
    "master_key": os.environ.get("LITELLM_MASTER_KEY", "internal-key"),
    "model_name": os.environ.get("MODEL_NAME", "qwen35b"),
    "cost_per_token": 0.0000001,
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
