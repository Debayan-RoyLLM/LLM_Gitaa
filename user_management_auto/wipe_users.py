#!/usr/bin/env python3
"""wipe_users.py — one-shot script to delete all LiteLLM users and their data.

Usage (from /home/gitaa/Desktop/LLM_API):
    python3 quota_desk/wipe_users.py          # dry-run: shows who would be deleted
    python3 quota_desk/wipe_users.py --confirm  # actually deletes everyone
"""

import json
import os
import sys
import urllib.request
import urllib.error

# ---------------------------------------------------------------------------
# Config — matches .env / config defaults. Override via env vars or here.
# ---------------------------------------------------------------------------

LITELLM_URL = os.environ.get("LITELLM_URL", "http://100.102.25.115:4000")
MASTER_KEY = os.environ.get("LITELLM_MASTER_KEY", "internal-key")


def _litellm(method, path, body=None):
    url = LITELLM_URL.rstrip("/") + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + MASTER_KEY)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
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


def main():
    confirm = "--confirm" in sys.argv

    if not confirm:
        print("DRY RUN — no users will be deleted.")
        print("Add --confirm to actually delete.")
        print()

    status, data = _litellm("GET", "/user/list")
    if status != 200:
        print(f"ERROR: Could not list users (status {status}): {data}")
        sys.exit(1)

    users = data if isinstance(data, list) else data.get("users", [])
    if not users:
        print("No users found. Nothing to do.")
        return

    print(f"Found {len(users)} user(s):\n")
    for u in users:
        uid = u.get("user_id", "<unknown>")
        keys = len(u.get("keys", [])) if isinstance(u.get("keys"), list) else 0
        spend = u.get("spend", 0)
        print(f"  - {uid:30s}  keys={keys:3d}  spend={spend:.6f}")
    print()

    if not confirm:
        print("Aborted. Re-run with --confirm to proceed.")
        return

    # Delete each user
    deleted = 0
    errors = 0
    for u in users:
        uid = u.get("user_id")
        if not uid:
            continue
        print(f"Deleting {uid}...", end=" ")
        status, result = _litellm("DELETE", "/user/delete", body={"user_id": uid})
        if status == 200:
            print("OK")
            deleted += 1
        else:
            print(f"FAIL ({status}): {result}")
            errors += 1

    print(f"\nDone. Deleted={deleted}  Errors={errors}")


if __name__ == "__main__":
    main()
