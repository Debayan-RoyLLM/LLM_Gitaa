# Architecture

Block-diagram reference for the Dockerized internal LLM stack.
For day-to-day operations (credentials, quick start, file map) see [README.md](README.md);
for runbook / incident procedures see [RUNBOOK.md](RUNBOOK.md).

## High-Level Overview

```
                         EXTERNAL CLIENTS
        ┌──────────────┐   ┌─────────────────────────┐   ┌──────────────────────┐
        │  LLM API     │   │  LLM clients            │   │  Admin / you          │
        │  consumers   │   │  (Claude Code, apps,    │   │  (token mgmt, quotas) │
        │  (any app)   │   │   scripts, agents)      │   │                       │
        └──────┬───────┘   └────────────┬────────────┘   └──────────┬────────────┘
               │  HTTPS :443            │  HTTPS :443               │ HTTPS :443
               └────────────┬───────────┘                          │
                            │  (single public door — TLS)          │
               ┌────────────▼──────────────────────────────────────▼───────────┐
               │                        NGINX  (443 ssl)                       │
               │              reverse proxy · TLS termination · HSTS           │
               └───────┬───────────────────────────────────────────┬───────────┘
                       │  location /                location /user/
                       │  (API, Bearer key)         (Basic Auth gate)
        ┌──────────────▼──────────────┐        ┌───────────────────▼──────────┐
        │        LITELLM proxy        │        │    USER console (Flask)      │
        │     (public API, :5000)     │        │      token/ quota UI :8080   │
        │                             │        └───────────────┬──────────────┘
        │  • auth (master/user keys)  │                        │ admin API (master key)
        │  • routing / retries        │                        │
        │  • Redis semantic cache     │                        │
        │  • Presidio PII guardrails  │                        │
        │  • merge_system callback    │                        │
        │  • Postgres metadata        │                        │
        └───┬────────┬────────┬───────┘                        │
            │        │        │                                 │
            │        │        │      ┌──────────────────────────┤
            │        │        │      │ (all over compose network)
```

## Service Map

| Service            | Image                          | Port (internal) | Exposed | Role                                    |
| ------------------ | ------------------------------ | --------------- | ------- | --------------------------------------- |
| `nginx`            | `nginx:1.27-alpine`            | 443 (ssl)       | **443** | TLS termination, reverse proxy, HSTS    |
| `litellm`          | `ghcr.io/berriai/litellm`      | 5000            | 4000*   | LLM gateway: auth, routing, cache, PII  |
| `vllm-qwen27b`     | `vllm/vllm-openai`             | 8007            | —       | Model server (Qwen3.8-27B, GPU, fp8)    |
| `presidio`         | built from `Dockerfile.presidio` | 5005          | —       | PII analyzer/anonymizer (guardrail)     |
| `user`             | built from `Dockerfile.user`   | 8080            | —       | Web console for LiteLLM tokens/quotas   |
| `postgres`         | `postgres:15-alpine`           | 5432            | 5432    | LiteLLM metadata store (keys, spend)    |
| `redis`            | `redis:7-alpine`               | 6379            | —       | Semantic cache (1 h TTL)                |

\* `4000:5000` is still mapped in `docker-compose.yaml`, but with nginx in front the
intended external door is **443 only**. The 4000 mapping can be removed if you want
TLS to be the sole entry point.

## Internal Network View

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                       compose network  (qwen27b)                              │
│                                                                                │
│   ┌──────────────┐   :8007/v1   ┌───────────────────┐                          │
│   │   vLLM       │◄──────────── │      LITELLM      │  pre_call guardrail      │
│   │  Qwen3.8-27B │  (internal,  │   :5000  ◄────────┼─────►┌───────────┐       │
│   │  GPU, fp8    │   no public  │                   │      │ PRESIDIO  │       │
│   │  /health     │   port)      │  auth / routing / │      │ PII :5005 │       │
│   └──────────────┘              │  cache / metadata │      └───────────┘       │
│        ▲                        └───────┬─────┬─────┘                          │
│        │ model weights (ro)             │     │                                │
│   ./Qwen3.8-27B                       │     │                                │
│                                        │     │                                │
│                              ┌─────────▼──┐  ┌▼──────────────┐                │
│                              │  REDIS     │  │  POSTGRES     │                │
│                              │  cache     │  │  metadata/    │                │
│                              │  (ttl 1h)  │  │  keys/quotas  │                │
│                              └────────────┘  └───────────────┘                │
└───────────────────────────────────────────────────────────────────────────────┘
```

- `vllm-qwen27b` and `presidio` have **no public ports** — they are reachable only
  by service name inside the compose network.
- `user` has **no public port** either; it is fronted by nginx under `/user/`
  behind HTTP Basic Auth.
- `postgres` is published on `5432` for local admin/debug access.

## Request Lifecycle

```
 ①  Client sends POST /v1/chat/completions  (HTTPS :443, Bearer key)
       │
 ②  NGINX  ── TLS termination, routes location / → litellm:5000
       │
 ③  LITELLM  ── authenticate (master_key / per-user token)
       │
 ④     └─► check REDIS semantic cache ── HIT? ──► return cached response  (done)
       │
 ⑤  Presidio PRE_CALL guardrails
       │     • CREDIT_CARD → BLOCK  (request rejected, never reaches model)
       │     • EMAIL / PHONE / US_SSN → MASK  (values redacted in-place)
       │
 ⑥  merge_system.py callback  (system messages merged for the Qwen template)
       │
 ⑦  router (least-busy, retries, cooldowns)  →  vLLM  :8007/v1
       │
 ⑧  vLLM runs Qwen3.8-27B (prefix-caching, chunked prefill, fp8 KV)
       │
 ⑨  streamed response back up:  vLLM → LiteLLM → NGINX → client
       │
 ⑩  LiteLLM logs spend/tokens to POSTGRES (spend tracking, key quotas)
```

## Cross-Cutting Concerns

### Auth — two independent layers

| Surface            | Mechanism                     | Where configured                          |
| ------------------ | ----------------------------- | ----------------------------------------- |
| LLM API (any path) | `Authorization: Bearer <key>` | `litellm_config.yaml` → `master_key`; per-user tokens in Postgres |
| User console       | nginx HTTP Basic Auth         | `nginx/.htpasswd` (applied to `/user/`)   |

### PII guardrails (in `litellm_config.yaml`)

| Guardrail    | Mode       | Entities                       | Action |
| ------------ | ---------- | ------------------------------ | ------ |
| `block-cc`   | `pre_call` | `CREDIT_CARD`                  | BLOCK  |
| `pii-mask`   | `pre_call` | `EMAIL_ADDRESS, PHONE_NUMBER, US_SSN` | MASK |

Both run before the request reaches vLLM, so PII is redacted (or the request
rejected) *before* the model ever sees it.

### Caching vs Persistence

| Store    | What it holds                                  | Persistence |
| -------- | ---------------------------------------------- | ----------- |
| Redis    | Semantic cache of completed responses (1 h TTL) | Ephemeral   |
| Postgres | API keys, spend, quotas, model registry        | `postgres-data` volume |

### Startup Ordering (`depends_on`)

```
vllm-qwen27b ──healthy──┐
redis        ──started──┼──► litellm ──started──► user ──started──► nginx
postgres     ──started──┘
```

- vLLM must be **healthy** (`/health` 200) before LiteLLM starts.
  Model load can take several minutes — `start_period: 600s`.
- Redis and Postgres only need to be **started**.
- User console starts after LiteLLM; nginx starts after both its upstreams.

### Key Flags on vLLM (see `docker-compose.yaml`)

- `--gpu-memory-utilization=0.95` — uses almost all VRAM
- `--enable-prefix-caching` + `--enable-chunked-prefill` — throughput features
- `--kv-cache-dtype=fp8` — halves KV-cache memory
- `--max-num-seqs=512`, `--max-num-batched-tokens=32768` — concurrency caps
- `--reasoning-parser=qwen3`, `--tool-call-parser=qwen3_coder` — Qwen3-specific
- `--default-chat-template-kwargs={"enable_thinking": false}` — no CoT by default

### Optional / Commented-Out Services

- **Second model** (`vllm-qwen9b` on 8008) — disabled in the compose file;
  requires a second GPU or lower `gpu-memory-utilization` on both.
- **Wild-card LiteLLM route** (`model_name: "*"`) — commented out in
  `litellm_config.yaml`; would forward any unknown model name to a fallback.
