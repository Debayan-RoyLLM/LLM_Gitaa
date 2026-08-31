"""File writers: env file, Claude Code settings, Qwen Code env, shell rc patch."""

import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

from .config import (
    CLAUDE_SETTINGS,
    ENV_FILE,
    MARK_END,
    MARK_START,
    QWEN_ENV,
    RC_CANDIDATES,
    RC_BLOCK,
)


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------

def normalize(url: str) -> str:
    """Return the gateway root: no trailing slash, no trailing /v1."""
    u = (url or "").strip().rstrip("/")
    if u.endswith("/v1"):
        u = u[:-3].rstrip("/")
    return u


def backup(path: Path) -> str:
    if not path.exists():
        return ""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = path.with_name(path.name + f".bak-{stamp}")
    shutil.copy2(path, dest)
    return str(dest)


def secure_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def parse_env(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        line = line[len("export "):].strip() if line.startswith("export ") else line
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def mask(key: str) -> str:
    if not key:
        return ""
    return key[:7] + "…" + key[-4:] if len(key) > 14 else "…" * len(key)


# ----------------------------------------------------------------------------
# file writers
# ----------------------------------------------------------------------------

def env_file_body(root: str, key: str, model: str, small_model: str) -> str:
    return f"""# Written by llm-gateway-setup.py on {datetime.now().strftime('%Y-%m-%d %H:%M')}
# Single source of truth for internal gateway access. Do not commit.

LLM_GATEWAY_URL="{root}"
LLM_API_KEY="{key}"
LLM_MODEL="{model}"

# Claude Code — Anthropic Messages format, no /v1 suffix
export ANTHROPIC_BASE_URL="$LLM_GATEWAY_URL"
export ANTHROPIC_AUTH_TOKEN="$LLM_API_KEY"
export ANTHROPIC_MODEL="{model}"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="{small_model}"
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1

# Qwen Code — OpenAI format, /v1 suffix required
export OPENAI_BASE_URL="$LLM_GATEWAY_URL/v1"
export OPENAI_API_KEY="$LLM_API_KEY"
export OPENAI_MODEL="{model}"
"""


def write_env(root, key, model, small, results):
    bak = backup(ENV_FILE)
    secure_write(ENV_FILE, env_file_body(root, key, model, small))
    results.append({"path": str(ENV_FILE), "action": "updated" if bak else "created", "backup": bak})


def write_claude(root, key, model, small, results):
    data = {}
    if CLAUDE_SETTINGS.exists():
        try:
            data = json.loads(CLAUDE_SETTINGS.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError:
            raise RuntimeError(
                f"{CLAUDE_SETTINGS} is not valid JSON. Fix or move it, then apply again."
            )
    bak = backup(CLAUDE_SETTINGS)
    data.setdefault("$schema", "https://json.schemastore.org/claude-code-settings.json")
    env = data.get("env") or {}
    env.update({
        "ANTHROPIC_BASE_URL": root,
        "ANTHROPIC_AUTH_TOKEN": key,
        "ANTHROPIC_MODEL": model,
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": small,
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    })
    data["env"] = env
    secure_write(CLAUDE_SETTINGS, json.dumps(data, indent=2) + "\n")
    results.append({"path": str(CLAUDE_SETTINGS), "action": "updated" if bak else "created", "backup": bak})


def write_qwen(root, key, model, results):
    body = (
        f"# Written by llm-gateway-setup.py on {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f'OPENAI_BASE_URL="{root}/v1"\n'
        f'OPENAI_API_KEY="{key}"\n'
        f'OPENAI_MODEL="{model}"\n'
    )
    bak = backup(QWEN_ENV)
    secure_write(QWEN_ENV, body)
    results.append({"path": str(QWEN_ENV), "action": "updated" if bak else "created", "backup": bak})


def patch_rc(results):
    if os.name == "nt":
        results.append({"path": "shell profile", "action": "skipped (Windows)", "backup": ""})
        return
    touched = False
    for rc in RC_CANDIDATES:
        if not rc.exists():
            continue
        text = rc.read_text(encoding="utf-8")
        cleaned = re.sub(
            re.escape(MARK_START) + r".*?" + re.escape(MARK_END) + r"\n?",
            "",
            text,
            flags=re.S,
        )
        bak = backup(rc)
        new = cleaned.rstrip("\n") + "\n\n" + RC_BLOCK + "\n"
        rc.write_text(new, encoding="utf-8")
        results.append({"path": str(rc), "action": "sourced env file", "backup": bak})
        touched = True
    if not touched:
        results.append({"path": "~/.zshrc or ~/.bashrc", "action": "not found — skipped", "backup": ""})
