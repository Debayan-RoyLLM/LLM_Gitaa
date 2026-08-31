"""Tool detection and background install jobs."""

import os
import re
import secrets
import shutil
import subprocess
import threading

from .config import EXTRA_BIN_DIRS, HOME, INSTALLERS, IS_WIN, TOOLS

JOBS = {}
JOBS_LOCK = threading.Lock()


# ----------------------------------------------------------------------------
# tool detection
# ----------------------------------------------------------------------------

def find_bin(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    for d in EXTRA_BIN_DIRS:
        for suffix in ((".cmd", ".exe", "") if IS_WIN else ("",)):
            cand = d / (name + suffix)
            if cand.is_file() and os.access(cand, os.X_OK):
                return str(cand)
    return ""


def bin_version(path: str) -> str:
    if not path:
        return ""
    try:
        r = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=25)
        line = (r.stdout or r.stderr or "").strip().splitlines()
        return line[0][:60] if line else ""
    except Exception:  # noqa: BLE001
        return ""


def node_major() -> int:
    v = bin_version(find_bin("node"))
    m = re.search(r"v?(\d+)", v)
    return int(m.group(1)) if m else 0


def detect_tools() -> dict:
    node_path = find_bin("node")
    npm_path = find_bin("npm")
    major = node_major() if node_path else 0
    tools = []
    for t in TOOLS:
        path = find_bin(t["bin"])
        tools.append({
            "id": t["id"],
            "label": t["label"],
            "bin": t["bin"],
            "note": t["note"],
            "found": bool(path),
            "path": path,
            "version": bin_version(path) if path else "",
        })
    return {
        "tools": tools,
        "node": {"found": bool(node_path), "major": major, "npm": bool(npm_path)},
        "on_path_warning": _path_warning(),
    }


def _path_warning() -> str:
    """Warn if a freshly installed CLI would land somewhere not on PATH."""
    if IS_WIN:
        return ""
    local_bin = HOME / ".local" / "bin"
    parts = (os.environ.get("PATH") or "").split(os.pathsep)
    if str(local_bin) not in parts:
        return (f"{local_bin} is not on your PATH. After installing, add it: "
                f'export PATH="$HOME/.local/bin:$PATH"')
    return ""


# ----------------------------------------------------------------------------
# install jobs
# ----------------------------------------------------------------------------

def start_install(tool_id: str, method: str) -> str:
    cmd = INSTALLERS[tool_id][method]
    job_id = secrets.token_hex(8)
    with JOBS_LOCK:
        JOBS[job_id] = {"lines": [f"$ {cmd}", ""], "done": False, "code": None, "verified": False}

    def worker():
        try:
            shell_exe = None if IS_WIN else "/bin/bash"
            # Without pipefail, `curl … | bash` reports success even when curl fails.
            run = cmd if IS_WIN else "set -o pipefail; " + cmd
            proc = subprocess.Popen(
                run, shell=True, executable=shell_exe,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, cwd=str(HOME),
                env={**os.environ, "npm_config_yes": "true"},
            )
            for line in proc.stdout:
                with JOBS_LOCK:
                    JOBS[job_id]["lines"].append(line.rstrip("\n")[:400])
                    if len(JOBS[job_id]["lines"]) > 500:
                        del JOBS[job_id]["lines"][:100]
            proc.wait(timeout=900)
            code = proc.returncode
        except Exception as e:  # noqa: BLE001
            with JOBS_LOCK:
                JOBS[job_id]["lines"].append(f"{type(e).__name__}: {e}")
            code = 1
        binary = next((t["bin"] for t in TOOLS if t["id"] == tool_id), tool_id)
        found = bool(find_bin(binary))
        with JOBS_LOCK:
            JOBS[job_id]["code"] = code
            JOBS[job_id]["verified"] = found
            if code == 0 and not found:
                JOBS[job_id]["lines"].append(
                    f"\nInstaller finished but '{binary}' is still not on PATH. "
                    "It may be in ~/.local/bin — open a new terminal and check with "
                    f"'which {binary}'.")
            JOBS[job_id]["done"] = True

    threading.Thread(target=worker, daemon=True).start()
    return job_id
