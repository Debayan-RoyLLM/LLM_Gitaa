#!/usr/bin/env python3

import subprocess
import os
import time
import sys
import urllib.request

CONFIG_FILE     = "./litellm_config.yaml"
MASTER_KEY      = "internal-key"

PRESIDIO_SCRIPT = "./presidio_server.py"
PRESIDIO_PORT   = 5005
PRESIDIO_BASE   = f"http://localhost:{PRESIDIO_PORT}"
PRESIDIO_LOG    = os.path.expanduser(f"~/presidio_{PRESIDIO_PORT}.log")


def presidio_healthy():
    try:
        with urllib.request.urlopen(f"{PRESIDIO_BASE}/health", timeout=2) as r:
            return r.read().decode().strip() == "ok"
    except Exception:
        return False


def start_presidio():
    if presidio_healthy():
        print(f"✅ Presidio already running on port {PRESIDIO_PORT}")
        return

    if not os.path.isfile(PRESIDIO_SCRIPT):
        print(f"❌ Presidio server not found: {PRESIDIO_SCRIPT}")
        sys.exit(1)

    print(f"🚀 Starting Presidio on port {PRESIDIO_PORT}...")
    env = {**os.environ, "PORT": str(PRESIDIO_PORT)}
    log = open(PRESIDIO_LOG, "w")
    # start_new_session keeps it alive after this script exits (like nohup)
    subprocess.Popen(
        [sys.executable, PRESIDIO_SCRIPT],
        env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
    )

    # wait for the spaCy model to load and /health to answer (up to ~60s)
    for _ in range(30):
        time.sleep(2)
        if presidio_healthy():
            print("✅ Presidio is up")
            return
    print(f"❌ Presidio failed to start. Check {PRESIDIO_LOG}")
    sys.exit(1)


def enable_guardrails():
    # LiteLLM (started below) inherits these and routes guardrails to Presidio
    os.environ["PRESIDIO_ANALYZER_API_BASE"]   = PRESIDIO_BASE
    os.environ["PRESIDIO_ANONYMIZER_API_BASE"] = PRESIDIO_BASE
    print("✅ Guardrail env vars set")


def kill_existing_litellm():
    print("🔴 Stopping existing LiteLLM process...")
    # use exact match to avoid killing this script itself
    result = subprocess.run(
        ["pkill", "-f", "litellm --config"],
        capture_output=True
    )
    if result.returncode == 0:
        print("✅ Killed existing LiteLLM")
        time.sleep(2)
    else:
        print("ℹ️  No existing LiteLLM process found")


def start_litellm(port="4000"):
    if not os.path.isfile(CONFIG_FILE):
        print(f"❌ Config file not found: {CONFIG_FILE}")
        sys.exit(1)

    result = subprocess.run(["which", "litellm"], capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ litellm not found. Install with: pip install litellm")
        sys.exit(1)

    print(f"\n🚀 Starting LiteLLM...")
    print(f"   Config : {CONFIG_FILE}")
    print(f"   Port   : {port}")

    cmd = ["litellm", "--config", CONFIG_FILE, "--port", port]
    process = subprocess.Popen(cmd)

    print(f"✅ LiteLLM started (PID: {process.pid})")
    print(f"\n🟢 LiteLLM running on port {port}. Press Ctrl+C to stop.\n")

    try:
        process.wait()
    except KeyboardInterrupt:
        print("\n🔴 Stopping LiteLLM...")
        process.terminate()
        process.wait()
        print("✅ Done.")


def main():
    port = input("Enter LiteLLM port [default: 4000]: ").strip() or "4000"
    start_presidio()        # 1. make sure the PII server is up
    enable_guardrails()     # 2. point LiteLLM at it
    kill_existing_litellm() # 3. clear any stale proxy
    start_litellm(port)     # 4. start the proxy (guardrails now active)


if __name__ == "__main__":
    main()
