"""
LiteLLM proxy pre-call hook.

Two jobs:

1. System-message flattening
   Qwen3.x chat templates raise "System message must be at the beginning."
   if a system message appears anywhere except index 0. Claude Code sends
   several system blocks (identity, env info, <system-reminder> injections),
   so after Anthropic -> OpenAI translation there is more than one.

2. reasoning_effort normalisation
   Claude Code sends Anthropic-style thinking: {budget_tokens: N}.
   LiteLLM translates that to OpenAI reasoning_effort, whose vocabulary is
   low / medium / high. Qwen3.8's chat template only accepts
   low / medium / xhigh -> vLLM returns:

       "Unexpected reasoning effort high. Supported types are
        xhigh (default), medium, and low."

   This hook maps any incoming value onto Qwen's three tiers.
"""

import os

from litellm.integrations.custom_logger import CustomLogger

# Qwen3.8 accepts exactly these three.
_QWEN_EFFORTS = {"low", "medium", "xhigh"}

# What "high" should become. xhigh is Qwen's own default, but on a shared box
# it produces very long <think> blocks and can eat the whole max_tokens budget
# before emitting an answer. medium is the safer default for 25+ users.
_HIGH_MAPS_TO = os.getenv("QWEN_HIGH_EFFORT", "medium")

_EFFORT_MAP = {
    "none": "low",
    "minimal": "low",
    "low": "low",
    "medium": "medium",
    "high": _HIGH_MAPS_TO,
    "xhigh": "xhigh",
    "max": "xhigh",
    "ultracode": "xhigh",
    "extreme": "xhigh",
}


def _to_text(content) -> str:
    """Content may be a str, a list of blocks, or None."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "\n".join(p for p in parts if p)
    return str(content)


class MergeSystem(CustomLogger):
    async def async_pre_call_hook(self, user_api_key_dict, cache, data, call_type):
        # ------------------------------------------------------------------
        # 1. reasoning_effort -> Qwen tiers
        # ------------------------------------------------------------------
        effort = data.pop("reasoning_effort", None)

        # An Anthropic thinking block may also survive translation. vLLM does
        # not understand it; drop it and let reasoning_effort carry the intent.
        thinking = data.pop("thinking", None)
        if effort is None and isinstance(thinking, dict):
            if thinking.get("type") == "enabled":
                effort = "high"

        if effort is not None:
            normalised = _EFFORT_MAP.get(str(effort).strip().lower())
            if normalised is None:
                normalised = "medium"
            if normalised in _QWEN_EFFORTS:
                data["reasoning_effort"] = normalised

        # ------------------------------------------------------------------
        # 2. Flatten system messages to a single block at index 0
        # ------------------------------------------------------------------
        messages = data.get("messages")
        if not isinstance(messages, list):
            return data

        system_parts = []

        # Anthropic-style top-level system field, if it survived translation.
        top_level = data.pop("system", None)
        if top_level:
            system_parts.append(_to_text(top_level))

        rest = []
        for msg in messages:
            if isinstance(msg, dict) and msg.get("role") == "system":
                text = _to_text(msg.get("content"))
                if text:
                    system_parts.append(text)
            else:
                rest.append(msg)

        if system_parts:
            merged = "\n\n".join(p for p in system_parts if p.strip())
            data["messages"] = [{"role": "system", "content": merged}] + rest
        else:
            data["messages"] = rest

        return data


merge_system_instance = MergeSystem()
