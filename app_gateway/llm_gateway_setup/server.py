"""HTTP server: request handler, routing, and the CLI entry point."""

import argparse
import json
import secrets
import ssl
import sys
import threading
import urllib.error
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import detect
from .config import ENV_FILE, INSTALLERS, IS_WIN, TOKEN
from .page import PAGE
from .probe import current_state, probe
from .writers import (
    normalize,
    parse_env,
    patch_rc,
    write_claude,
    write_env,
    write_qwen,
)


class Handler(BaseHTTPRequestHandler):
    server_version = "gateway-setup"

    def log_message(self, *_):
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _authed(self) -> bool:
        return secrets.compare_digest(self.headers.get("X-Setup-Token", ""), TOKEN)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            self._send(200, PAGE.replace("__TOKEN__", TOKEN), "text/html")
        elif path == "/api/status":
            if not self._authed():
                return self._send(403, json.dumps({"ok": False, "error": "bad token"}))
            self._send(200, json.dumps(current_state()))
        elif path == "/api/detect":
            if not self._authed():
                return self._send(403, json.dumps({"ok": False, "error": "bad token"}))
            self._send(200, json.dumps(detect.detect_tools()))
        elif path == "/api/install":
            if not self._authed():
                return self._send(403, json.dumps({"ok": False, "error": "bad token"}))
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            job_id = (qs.get("job") or [""])[0]
            with detect.JOBS_LOCK:
                job = detect.JOBS.get(job_id)
                payload = dict(job) if job else None
            if payload is None:
                return self._send(404, json.dumps({"ok": False, "error": "no such job"}))
            self._send(200, json.dumps({"ok": True, **payload}))
        else:
            self._send(404, json.dumps({"ok": False, "error": "not found"}))

    def do_POST(self):
        if not self._authed():
            return self._send(403, json.dumps({"ok": False, "error": "bad token"}))
        length = int(self.headers.get("Content-Length") or 0)
        try:
            req = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._send(400, json.dumps({"ok": False, "error": "bad request body"}))

        if self.path == "/api/test":
            self._send(200, json.dumps(self._test(req)))
        elif self.path == "/api/apply":
            self._send(200, json.dumps(self._apply(req)))
        elif self.path == "/api/install":
            self._send(200, json.dumps(self._install(req)))
        else:
            self._send(404, json.dumps({"ok": False, "error": "not found"}))

    # -- handlers ------------------------------------------------------------

    def _resolve_key(self, given: str) -> str:
        if given.strip():
            return given.strip()
        if ENV_FILE.exists():
            return parse_env(ENV_FILE.read_text(encoding="utf-8")).get("LLM_API_KEY", "")
        return ""

    def _install(self, req):
        tool = req.get("tool")
        method = req.get("method", "native")
        if tool not in INSTALLERS or method not in INSTALLERS[tool]:
            return {"ok": False, "error": "Unknown tool or install method."}
        if method == "npm":
            if not detect.find_bin("npm"):
                return {"ok": False, "error": "npm is not installed. Use the native installer, "
                                              "or install Node.js 22+ first."}
            major = detect.node_major()
            if tool == "qwen" and major and major < 22:
                return {"ok": False, "error": f"Qwen Code needs Node.js 22 or later; you have {major}. "
                                              "npm would quietly install an old version instead. "
                                              "Upgrade Node, or use the native installer."}
        if method == "native" and not IS_WIN and not detect.find_bin("curl"):
            return {"ok": False, "error": "curl is not available. Install it, or use the npm method."}
        return {"ok": True, "job": detect.start_install(tool, method),
                "cmd": INSTALLERS[tool][method]}

    def _test(self, req):
        root = normalize(req.get("url", ""))
        key = self._resolve_key(req.get("key", ""))
        if not root.startswith(("http://", "https://")):
            return {"ok": False, "reached": 0, "error": "Enter a full URL starting with http:// or https://"}
        if not key:
            return {"ok": False, "reached": 0, "error": "Enter your API key."}
        try:
            return probe(root, key, bool(req.get("insecure")))
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                return {"ok": False, "reached": 3,
                        "error": f"Gateway reached, but it rejected the key (HTTP {e.code}).\n"
                                 "Check the virtual key in LiteLLM."}
            return {"ok": False, "reached": 3,
                    "error": f"Gateway reached, but returned HTTP {e.code}.\n"
                             "Confirm LiteLLM is serving /v1/models on this address."}
        except urllib.error.URLError as e:
            reason = getattr(e, "reason", e)
            if isinstance(reason, ssl.SSLError) or "CERTIFICATE" in str(reason).upper():
                return {"ok": False, "reached": 2,
                        "error": f"TLS failed: {reason}\n"
                                 "Use Tailscale Serve for a valid cert, or tick the certificate box."}
            return {"ok": False, "reached": 1,
                    "error": f"Could not reach the gateway: {reason}\n"
                             "Check that Tailscale is up and the hostname is right."}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "reached": 1, "error": f"{type(e).__name__}: {e}"}

    def _apply(self, req):
        root = normalize(req.get("url", ""))
        key = self._resolve_key(req.get("key", ""))
        model = (req.get("model") or "").strip()
        small = (req.get("small") or "").strip() or model
        targets = req.get("targets") or {}

        if not root.startswith(("http://", "https://")):
            return {"ok": False, "error": "Enter a full URL starting with http:// or https://"}
        if not key:
            return {"ok": False, "error": "Enter your API key."}
        if not model:
            return {"ok": False, "error": "Enter a model name. Run the connection test to list what your gateway offers."}
        if not any(targets.values()):
            return {"ok": False, "error": "Pick at least one place to write the configuration."}

        results = []
        try:
            if targets.get("env"):
                write_env(root, key, model, small, results)
            if targets.get("claude"):
                write_claude(root, key, model, small, results)
            if targets.get("qwen"):
                write_qwen(root, key, model, results)
            if targets.get("rc"):
                if not targets.get("env"):
                    return {"ok": False, "error": "Loading on every terminal needs the shared env file. Tick that too."}
                patch_rc(results)
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}
        return {"ok": True, "results": results}


def main():
    ap = argparse.ArgumentParser(description="Local setup UI for internal LLM gateway access.")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1",
                    help="interface to bind (default 127.0.0.1; use 0.0.0.0 inside a container)")
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    try:
        httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    except OSError as e:
        print(f"Could not start on port {args.port}: {e}\nTry --port 8790", file=sys.stderr)
        sys.exit(1)

    url = f"http://{args.host}:{args.port}/"
    local = args.host in ("127.0.0.1", "localhost")
    print(f"\n  Gateway setup running at {url}")
    print("  Listening on localhost only. Press Ctrl-C to stop.\n" if local
          else "  Listening on all interfaces. Press Ctrl-C to stop.\n")
    if not args.no_browser and local:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("  Stopped.")


if __name__ == "__main__":
    main()
