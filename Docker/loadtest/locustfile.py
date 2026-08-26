"""Load test for the internal Qwen-27B stack (LiteLLM :4000) — 3 workloads.

Workloads:
  summarization : long prompt (~1.5k tokens) in, short answer (~150) out
  qa            : short prompt in, short answer out
  agentic       : chat + tools, code-heavy, multi-turn sessions (~2k out)

Pick ONE per run (mixing workloads in one run muddies the metrics):
  LOCUSTFILE_WORKLOAD=summarization  locust --headless ...
  LOCUSTFILE_WORKLOAD=qa             locust --headless ...
  LOCUSTFILE_WORKLOAD=agentic        locust --headless ...
"""
import os
import random

from locust import HttpUser, between, task

API_KEY = os.environ.get("LITELLM_MASTER_KEY", "internal-key")
MODEL = os.environ.get("LITELLM_MODEL", "qwen27b")
WORKLOAD = os.environ.get("LOCUSTFILE_WORKLOAD", "all")

# ---------------------------------------------------------------------------
# prompt pools — realistic shapes, distinct content per prompt so the
# redis semantic cache (ttl 3600s) does NOT serve hits and inflate the numbers
# ---------------------------------------------------------------------------

_FILLER = (
    "The quarterly report shows revenue up 12 percent year over year, "
    "driven by expansion in three new regions and the launch of two products. "
    "Operating costs rose 4 percent, mostly from infrastructure and hiring. "
    "Customer churn remained flat at 2.1 percent, while net promoter score "
    "improved from 41 to 47 following the support reorganization in Q1. "
)

def _make_doc(kind: str, i: int) -> str:
    salt = random.randbytes(8).hex()
    if kind == "section":
        return (
            _FILLER * 8
            + f"Section {i} additional detail: {'alpha' if i % 3 else 'beta'} "
            f"metrics {salt} were tracked against the roadmap targets."
        )
    return (
        _FILLER * 10
        + f"Appendix {i} 'A' * 20: variance analysis for the {i}-th "
        f"business unit, covering headcount, spend, and delivery commitments {salt}."
    )


SUMMARIZATION_DOCS = [_make_doc(k, i) for i in range(40) for k in ("section", "appendix")]

QA_QUESTIONS = [
    "What is the difference between a process and a thread in an OS?",
    "Explain the trade-offs of a B-tree vs a skip list as an index.",
    "Why does Docker need the NVIDIA container toolkit to see a GPU?",
    "What is prefix caching in LLM inference and when does it help?",
    "How does connection pooling work in a PostgreSQL proxy?",
    "Explain the difference between eventual and strong consistency.",
    "What happens to a request when a KV cache slot is preempted in vLLM?",
    "Summarize the main failure modes of REST rate limiting.",
]

# agentic coding: one tool each agent (like Claude Code) would likely use
AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_bash",
            "description": "Run a shell command in the project directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The command to run"}
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"}
                },
                "required": ["path"],
            },
        },
    },
]

AGENT_TASKS = [
    "The tests in test_api.py are failing with a 500 on /v1/chat/completions "
    "when the request has no 'model' field. Debug and fix the handler in "
    "server.py so it returns a proper 400 validation error instead. "
    "First run the tests to see the failure, then inspect the code.",
    "Add retry logic with exponential backoff to the http_client.py module. "
    "Retry up to 3 times on 502/503 responses, doubling the delay starting at "
    "1 second. Read the file first, then show your plan before editing.",
    "Refactor the rate limiter in limiter.py from a fixed window to a "
    "sliding window implementation. Read the existing code, write the new "
    "implementation, and update the docstring.",
]


class LLMUser(HttpUser):
    """One simulated user of the LLM application."""

    # small think-time between requests so a user does not fire back-to-back
    wait_time = between(1, 3)

    # per-workload concurrency caps; Locust scales each user class up to
    # users//len(user_classes) rounded — keep the three in the same file run
    # separate for clean per-workload metrics (see run.sh)

    def on_start(self):
        self.client.headers.update({"Authorization": f"Bearer {API_KEY}"})
        self._turn = 0
        self._session_msgs = [
            {
                "role": "system",
                "content": (
                    "You are a coding agent working in a Python project. "
                    "You may call tools: run_bash, read_file. When you are "
                    "done, give the final answer in a short code summary."
                ),
            }
        ]

    # ------------------------------------------------------------------ #
    @task
    def summarization(self):
        if WORKLOAD not in ("all", "summarization"):
            return
        doc = random.choice(SUMMARIZATION_DOCS)
        self.client.post(
            "/v1/chat/completions",
            name="summarization",
            json={
                "model": MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "Summarize the document in 3 bullet points.",
                    },
                    {"role": "user", "content": doc},
                ],
                "max_tokens": 300,
                "temperature": 0.3,
            },
        )

    @task
    def qa(self):
        if WORKLOAD not in ("all", "qa"):
            return
        self.client.post(
            "/v1/chat/completions",
            name="qa",
            json={
                "model": MODEL,
                "messages": [
                    {"role": "user", "content": random.choice(QA_QUESTIONS)}
                ],
                "max_tokens": 300,
                "temperature": 0.2,
            },
        )

    @task
    def agentic(self):
        if WORKLOAD not in ("all", "agentic"):
            return
        # multi-turn: up to 3 rounds of "model -> (pretend tool result) -> model"
        # to mimic a real agentic loop without needing an actual sandbox.
        if self._turn == 0:
            self._session_msgs.append(
                {"role": "user", "content": random.choice(AGENT_TASKS)}
            )
        else:
            self._session_msgs.append(
                {
                    "role": "user",
                    "content": "Tool output: <ok> done. Continue and finish the task.",
                }
            )
        self.client.post(
            "/v1/chat/completions",
            name=f"agentic_turn_{min(self._turn + 1, 3)}",
            json={
                "model": MODEL,
                "messages": self._session_msgs,
                "tools": AGENT_TOOLS,
                "tool_choice": "auto",
                "max_tokens": 2048,
                "temperature": 0.2,
            },
        )
        self._turn = (self._turn + 1) % 3


