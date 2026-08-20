#!/usr/bin/env python3
"""user_management_auto.server — HTTP handler and entry point."""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .config import CONFIG, save_config
from .api import call_litellm, stack_status, list_keys, get_total_tokens_for_user


class Handler(BaseHTTPRequestHandler):
    """Thin HTTP router that delegates to api.py / config."""

    server_version = "UserManagementAuto/1.0"

    def log_message(self, fmt, *args):
        pass  # keep the console quiet; this is a foreground tool

    # -- response helpers --------------------------------------------------

    def _send(self, status, payload, ctype="application/json"):
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode())
        except ValueError:
            return {}

    # -- GET routes --------------------------------------------------------

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, PAGE.encode(), "text/html; charset=utf-8")
        elif self.path == "/api/config":
            safe = dict(CONFIG)
            safe["master_key"] = "•" * 8 if CONFIG["master_key"] else ""
            self._send(200, safe)
        elif self.path == "/api/status":
            self._send(200, {"services": stack_status()})
        elif self.path == "/api/users":
            # Derive user list from keys (LiteLLM may not have user objects)
            status, data = list_keys(params={"return_full_object": "true"})
            if status != 200:
                self._send(status, data)
                return
            keys = data.get("keys", data.get("data", []))
            # Group keys by user_id
            users_map = {}
            for k in keys:
                if not isinstance(k, dict):
                    continue
                uid = k.get("user_id") or "unassigned"
                if uid not in users_map:
                    users_map[uid] = {"user_id": uid, "keys": [], "spend": 0, "max_budget": 0}
                users_map[uid]["keys"].append(k)
                users_map[uid]["spend"] += k.get("spend", 0)
                if k.get("max_budget"):
                    users_map[uid]["max_budget"] = max(users_map[uid]["max_budget"], k["max_budget"])
            users = list(users_map.values())
            self._send(200, {"users": users})
        elif self.path.startswith("/api/users/tokens/"):
            user_id = self.path[len("/api/users/tokens/"):]
            if not user_id:
                self._send(400, {"error": "user_id is required"})
            else:
                status, data = get_total_tokens_for_user(user_id)
                self._send(status, data)
        else:
            self._send(404, {"error": "No such page."})

    # -- POST routes -------------------------------------------------------

    def do_POST(self):
        payload = self._read_json()
        if self.path == "/api/config":
            _save_config(payload)
            self._send(200, {"saved": True})
        elif self.path == "/api/lite":
            status, data = call_litellm(
                payload.get("method", "GET"),
                payload.get("path", "/"),
                payload.get("body"),
            )
            self._send(200, {"status": status, "data": data})
        else:
            self._send(404, {"error": "No such action."})


def _save_config(payload):
    """Apply POST /api/config changes and persist to disk."""
    for key in ("litellm_url", "vllm_url", "model_name"):
        if payload.get(key):
            CONFIG[key] = payload[key].strip()
    if payload.get("master_key"):
        CONFIG["master_key"] = payload["master_key"].strip()
    try:
        rate = float(payload.get("cost_per_token") or CONFIG["cost_per_token"])
        if rate > 0:
            CONFIG["cost_per_token"] = rate
    except (TypeError, ValueError):
        pass
    save_config()


# --------------------------------------------------------------------------
# embed the full PAGE (CSS + JS) from html_page.py
# --------------------------------------------------------------------------
from .html_page import PAGE


# --------------------------------------------------------------------------
# CLI entry point
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Web console for LiteLLM token quotas.")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--litellm", help="LiteLLM base URL")
    parser.add_argument("--vllm", help="vLLM base URL")
    parser.add_argument("--master-key", help="LiteLLM master key")
    parser.add_argument("--cost-per-token", type=float, help="must match litellm_config.yaml")
    args = parser.parse_args()

    from .config import load_config

    load_config()
    if args.litellm:
        CONFIG["litellm_url"] = args.litellm
    if args.vllm:
        CONFIG["vllm_url"] = args.vllm
    if args.master_key:
        CONFIG["master_key"] = args.master_key
    if args.cost_per_token:
        CONFIG["cost_per_token"] = args.cost_per_token
    save_config()

    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print("User Management on http://" + args.host + ":" + str(args.port))
    print("  LiteLLM : " + CONFIG["litellm_url"])
    print("  vLLM    : " + CONFIG["vllm_url"])
    print("  Rate    : " + str(CONFIG["cost_per_token"]) + " per token")
    print("Ctrl-C to stop.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
