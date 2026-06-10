#!/usr/bin/env python3

import subprocess
import os
import time
import sys

CONFIG_FILE = "./litellm_config.yaml"
MASTER_KEY  = "internal-key"


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
    kill_existing_litellm()
    start_litellm(port)


if __name__ == "__main__":
    main()
