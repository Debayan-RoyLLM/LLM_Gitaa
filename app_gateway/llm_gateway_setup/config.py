"""Constants, file paths, and tool/installer definitions for the gateway setup UI."""

import os
import secrets
from pathlib import Path

HOME = Path.home()
ENV_FILE = HOME / ".config" / "internal-llm" / "env"
CLAUDE_SETTINGS = HOME / ".claude" / "settings.json"
QWEN_ENV = HOME / ".qwen" / ".env"
RC_CANDIDATES = [HOME / ".zshrc", HOME / ".bashrc"]

MARK_START = "# >>> internal-llm gateway >>>"
MARK_END = "# <<< internal-llm gateway <<<"
RC_BLOCK = f"""{MARK_START}
[ -f "$HOME/.config/internal-llm/env" ] && . "$HOME/.config/internal-llm/env"
{MARK_END}"""

TOKEN = secrets.token_urlsafe(24)
IS_WIN = os.name == "nt"

# Places a global CLI can land that may not be on this process's PATH yet.
EXTRA_BIN_DIRS = [
    HOME / ".local" / "bin",
    HOME / "bin",
    HOME / ".npm-global" / "bin",
    Path("/usr/local/bin"),
    Path("/opt/homebrew/bin"),
]

# Fixed command strings. Never interpolate user input into these.
INSTALLERS = {
    "claude": {
        "native": (
            'irm https://claude.ai/install.ps1 | iex' if IS_WIN
            else 'curl -fsSL https://claude.ai/install.sh | bash'
        ),
        "npm": "npm install -g @anthropic-ai/claude-code@latest",
    },
    "qwen": {
        "native": (
            'irm https://qwen-code-assets.oss-cn-hangzhou.aliyuncs.com/installation/'
            'install-qwen-standalone.ps1 | iex' if IS_WIN
            else 'curl -fsSL https://qwen-code-assets.oss-cn-hangzhou.aliyuncs.com/'
                 'installation/install-qwen-standalone.sh | bash'
        ),
        "npm": "npm install -g @qwen-code/qwen-code@latest",
    },
}

TOOLS = [
    {"id": "claude", "label": "Claude Code", "bin": "claude",
     "note": "Native installer bundles its own runtime — no Node.js needed."},
    {"id": "qwen", "label": "Qwen Code", "bin": "qwen",
     "note": "Standalone archive if available, otherwise npm with Node.js 22+."},
]
