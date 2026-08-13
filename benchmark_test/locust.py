"""
locustfile.py
=============
Locust load-test runner for LLM backends behind a LiteLLM proxy.

Usage:
    locust -f locustfile.py --host http://localhost:4000

Test data lives in test_cases.py (prompts, SQL schemas, etc.)
so this file stays short and easy to tweak.
"""

from locust import HttpUser, task, between
import random

from test_cases import PROMPTS, SQL_TEST_CASES, SYSTEM_PROMPT_SQL, build_sql_prompt


# ──────────────────────────────────────────────────────────────
# LiteLLM proxy config
# Model keys must match `model_name` in your proxy_config.yaml
# ──────────────────────────────────────────────────────────────

LITELLM_MODELS = {
    "llama-3.2-3b":          "llama-3.2-3b",
    "gemma-3-12b":           "gemma-3-12b",
    "gemma-4-31b":           "gemma-4-31b",
    "qwen3.5-27b-reasoning": "qwen3.5-27b-reasoning",
}

# Change these to switch which models get tested
ACTIVE_MODEL_01 = "llama-3.2-3b"       # used by general prompts
ACTIVE_MODEL_02 = "gemma-3-12b"        # used by text-to-SQL
ACTIVE_MODEL_03 = "gemma-4-31b"        # used by text-to-SQL

# Must match general_settings.master_key in your LiteLLM YAML
LITELLM_MASTER_KEY = "internal-key"


def litellm_headers():
    """Build headers for LiteLLM proxy requests."""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LITELLM_MASTER_KEY}",
    }


# ──────────────────────────────────────────────────────────────
# Locust User
# ──────────────────────────────────────────────────────────────

class LLMUser(HttpUser):
    wait_time = between(1, 3)

    # ── Task 1: General prompts on MODEL_01 (weight 3) ────────
    @task(3)
    def chat_general(self):
        """General prompts — coding, reasoning, creative, etc."""
        model = LITELLM_MODELS[ACTIVE_MODEL_01]
        with self.client.post(
            "/v1/chat/completions",
            headers=litellm_headers(),
            json={
                "model": model,
                "messages": [
                    {"role": "user", "content": random.choice(PROMPTS)},
                ],
                "max_tokens": random.choice([64, 128, 256, 512]),
            },
            timeout=180,
            name=f"/v1/chat/completions [general][{ACTIVE_MODEL_01}]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                print(f"GENERAL FAILED [{response.status_code}]: {response.text[:300]}")
                response.failure(f"HTTP {response.status_code}")

    # ── Task 2: Text-to-SQL on MODEL_02 (weight 2) ────────────
    @task(2)
    def chat_text_to_sql(self):
        """Text-to-SQL — complex schema + question → SQL generation."""
        tc = random.choice(SQL_TEST_CASES)
        model = LITELLM_MODELS[ACTIVE_MODEL_02]
        with self.client.post(
            "/v1/chat/completions",
            headers=litellm_headers(),
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT_SQL},
                    {"role": "user", "content": build_sql_prompt(tc)},
                ],
                "max_tokens": 256,      # SQL queries rarely exceed 256 tokens
                "temperature": 0.1,
            },
            timeout=120,             # fail fast instead of hanging 5 min
            name=f"/v1/chat/completions [text-to-sql][{ACTIVE_MODEL_02}]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                print(f"SQL FAILED [{response.status_code}]: {response.text[:300]}")
                response.failure(f"HTTP {response.status_code}")

    # ── Task 3: Text-to-SQL on MODEL_03 (weight 2) ────────────
    @task(2)
    def chat_text_to_sql_gemma31b(self):
        """Text-to-SQL on gemma-4-31b — same prompts, bigger model."""
        tc = random.choice(SQL_TEST_CASES)
        model = LITELLM_MODELS[ACTIVE_MODEL_03]
        with self.client.post(
            "/v1/chat/completions",
            headers=litellm_headers(),
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT_SQL},
                    {"role": "user", "content": build_sql_prompt(tc)},
                ],
                "max_tokens": 256,
                "temperature": 0.1,
            },
            timeout=180,             # 31b needs more time than 12b
            name=f"/v1/chat/completions [text-to-sql][{ACTIVE_MODEL_03}]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                print(f"SQL-31B FAILED [{response.status_code}]: {response.text[:300]}")
                response.failure(f"HTTP {response.status_code}")

