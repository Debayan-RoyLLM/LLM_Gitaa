"""
LiteLLM proxy pre-call hook.

Qwen3.x chat templates raise System message must be at the beginning. if a
system message appears anywhere except index 0. Claude Code sends several
system blocks (identity, env info, <system-reminder> injections), so after
Anthropic -> OpenAI translation there is more than one.

This hook flattens every system message (and the Anthropic-style top-level
system field) into a single system message at index 0.
"""

from litellm.integrations.custom_logger import CustomLogger


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
