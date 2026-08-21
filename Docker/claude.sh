set -euo pipefail

BASE_URL="${LITELLM_BASE_URL:-https://user.tail02e79b.ts.net}"

# ------------------------------------------------------------ 1. model
MODEL="${1:-}"
[[ $# -gt 0 ]] && shift || true

while [[ -z "$MODEL" ]]; do
  read -rp "Model name (e.g. qwen35b): " MODEL
  MODEL="$(printf '%s' "$MODEL" | tr -d '[:space:]')"
  [[ -n "$MODEL" ]] || echo "  Model name cannot be empty."
done

# -------------------------------------------------------------- 2. key
# read -s keeps the key off the screen and out of shell history.
while true; do
  read -rsp "API key for ${MODEL}: " API_KEY
  echo
  API_KEY="$(printf '%s' "$API_KEY" | tr -d '[:space:]')"
  [[ -n "$API_KEY" ]] && break
  echo "  API key cannot be empty."
done

# ----------------------------------------------------- 3. verify access
# Confirms the key works AND the model is actually loaded, before
# handing off to Claude Code. A 35B can take minutes to come up.
echo "Checking ${MODEL} on ${BASE_URL} ..."

HTTP_CODE="$(
  curl -sS -o /dev/null -w '%{http_code}' --max-time 30 \
    "${BASE_URL}/v1/messages" \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "content-type: application/json" \
    -d "{\"model\":\"${MODEL}\",\"max_tokens\":8,
         \"messages\":[{\"role\":\"user\",\"content\":\"hi\"}]}" \
  || echo "000"
)"

case "$HTTP_CODE" in
  200) echo "  ok" ;;
  000) echo "  Cannot reach ${BASE_URL} (network, DNS, or TLS)." >&2; exit 1 ;;
  401|403) echo "  Rejected (HTTP $HTTP_CODE) - wrong API key." >&2; exit 1 ;;
  400) echo "  HTTP 400 - model '${MODEL}' not in the proxy's model_list?" >&2; exit 1 ;;
  404) echo "  HTTP 404 - is /v1/messages enabled on the proxy?" >&2; exit 1 ;;
  5*)  echo "  HTTP $HTTP_CODE - proxy reachable but upstream failed." >&2
       echo "  The model may still be loading; check its container logs." >&2; exit 1 ;;
  *)   echo "  Unexpected HTTP $HTTP_CODE." >&2; exit 1 ;;
esac

# ---------------------------------------------------------- 4. env vars
export ANTHROPIC_BASE_URL="$BASE_URL"
export ANTHROPIC_AUTH_TOKEN="$API_KEY"
export ANTHROPIC_API_KEY=""              # must stay empty or it overrides BASE_URL

# All tiers point at one model: Claude Code makes background haiku-tier
# calls that would otherwise request a model the proxy does not serve.
export ANTHROPIC_MODEL="$MODEL"
export ANTHROPIC_DEFAULT_OPUS_MODEL="$MODEL"
export ANTHROPIC_DEFAULT_SONNET_MODEL="$MODEL"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="$MODEL"
export CLAUDE_CODE_SUBAGENT_MODEL="$MODEL"

export CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT=1
export CLAUDE_CODE_MAX_OUTPUT_TOKENS="${CLAUDE_CODE_MAX_OUTPUT_TOKENS:-8192}"
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
export DISABLE_TELEMETRY=1
export DISABLE_ERROR_REPORTING=1
export DISABLE_AUTOUPDATER=1

echo
echo "  endpoint : $BASE_URL"
echo "  model    : $MODEL"
echo

exec claude "$@"
