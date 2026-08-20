#!/usr/bin/env python3
"""user_management_auto.api — talk to LiteLLM, probe local services."""

import json
import os
import socket
import urllib.error
import urllib.request

from .config import CONFIG

# --------------------------------------------------------------------------
# talking to LiteLLM
# --------------------------------------------------------------------------

def call_litellm(method, path, body=None, timeout=20):
    url = CONFIG["litellm_url"].rstrip("/") + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + CONFIG["master_key"])
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            return exc.code, json.loads(raw)
        except ValueError:
            return exc.code, {"error": raw[:500]}
    except urllib.error.URLError as exc:
        return 503, {"error": "Cannot reach LiteLLM at " + url + " (" + str(exc.reason) + ")"}
    except socket.timeout:
        return 504, {"error": "LiteLLM did not answer in time."}


# --------------------------------------------------------------------------
# service probes
# --------------------------------------------------------------------------

def port_open(port, host="127.0.0.1", timeout=1.5):
    try:
        with socket.create_connection((host, port), timeout):
            return True
    except OSError:
        return False


def http_alive(url, timeout=3):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except urllib.error.HTTPError:
        return True
    except Exception:
        return False


def _port_of(url):
    tail = url.rsplit(":", 1)[-1]
    tail = tail.split("/")[0]
    return int(tail) if tail.isdigit() else 0


def stack_status():
    return [
        {"name": "Postgres", "port": CONFIG["postgres_port"],
         "up": port_open(CONFIG["postgres_port"]),
         "fix": "pg_ctlcluster 16 main start"},
        {"name": "Redis", "port": CONFIG["redis_port"],
         "up": port_open(CONFIG["redis_port"]),
         "fix": "redis-server --daemonize yes"},
        {"name": "vLLM", "port": _port_of(CONFIG["vllm_url"]),
         "up": http_alive(CONFIG["vllm_url"].rstrip("/") + "/health"),
         "fix": "MODEL_NAME=" + CONFIG["model_name"] + " nohup python3 start_model.py > vllm.log 2>&1 &"},
        {"name": "LiteLLM", "port": _port_of(CONFIG["litellm_url"]),
         "up": http_alive(CONFIG["litellm_url"].rstrip("/") + "/health/liveliness"),
         "fix": "python3 start_litellm.py"},
    ]


# --------------------------------------------------------------------------
# LiteLLM user management
# --------------------------------------------------------------------------

def list_users():
    """Return all users from LiteLLM (GET /user/list)."""
    return call_litellm("GET", "/user/list")


def list_keys(params=None):
    """Return all keys from LiteLLM (GET /key/list)."""
    path = "/key/list"
    if params:
        q = "&".join(k + "=" + str(v) for k, v in params.items())
        path += "?" + q
    return call_litellm("GET", path)


def get_total_tokens_for_user(user_id):
    """Return total_tokens from LiteLLM /model/info for a specific user.

    Calls GET /model/info with body {user_id: ...}.
    Returns (status_code, {"total_tokens": int} or {"error": str}).
    """
    return call_litellm("GET", "/model/info", body={"user_id": user_id})


def delete_user(user_id):
    """Permanently delete a user and all their keys/logs (DELETE /user/delete)."""
    return call_litellm("DELETE", "/user/delete", body={"user_id": user_id})
