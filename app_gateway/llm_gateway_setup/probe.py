"""Gateway probe and current-state reporting."""

import json
import ssl
import time
import urllib.request

from .config import CLAUDE_SETTINGS, ENV_FILE, QWEN_ENV
from .writers import mask, parse_env


def probe(root: str, key: str, insecure: bool) -> dict:
    ctx = ssl.create_default_context()
    if insecure:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(
        root + "/v1/models",
        headers={
            "Authorization": f"Bearer {key}",
            "x-api-key": key,
            "Accept": "application/json",
        },
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=12, context=ctx) as resp:
        raw = resp.read().decode("utf-8", "replace")
    ms = int((time.time() - t0) * 1000)
    models = []
    try:
        payload = json.loads(raw)
        for item in payload.get("data", []):
            mid = item.get("id") or item.get("model_name")
            if mid:
                models.append(mid)
    except json.JSONDecodeError:
        pass
    return {"ok": True, "ms": ms, "models": sorted(set(models))}


def current_state() -> dict:
    state = {"url": "", "key_masked": "", "model": "", "files": []}
    if ENV_FILE.exists():
        vals = parse_env(ENV_FILE.read_text(encoding="utf-8"))
        state["url"] = vals.get("LLM_GATEWAY_URL", "")
        state["key_masked"] = mask(vals.get("LLM_API_KEY", ""))
        state["model"] = vals.get("LLM_MODEL", "") or vals.get("ANTHROPIC_MODEL", "")
    for label, p in (
        ("Shared env file", ENV_FILE),
        ("Claude Code", CLAUDE_SETTINGS),
        ("Qwen Code", QWEN_ENV),
    ):
        state["files"].append({"label": label, "path": str(p), "exists": p.exists()})
    return state
