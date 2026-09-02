# Runbook — Dockerized vLLM + LiteLLM + Redis + Postgres stack

Follow this on a machine where you have **root + a real Docker daemon + an NVIDIA GPU**
(a plain GPU VM or a privileged pod — NOT an unprivileged managed pod).

Stack (see `docker-compose.yaml`):

```
                ┌─────────────────────────────────────────────────────┐
                │  compose project name: qwen27b                       │
                │                                                       │
  LLM traffic ──▶ litellm :4000  ──▶ vllm-qwen27b :8007 (GPU)           │
                │        │   ▲                                         │
                │        │   └── presidio :5005 (PII guardrails)       │
                │        ├──▶ redis :6379 (semantic cache)             │
                │        └──▶ postgres :5432 (LiteLLM metadata + keys) │
                │                                                       │
  console ─────▶ <domain>/user/ (basic-auth gate) ─▶ user :8080        │
                └─────────────────────────────────────────────────────┘
```

- **vllm-qwen27b** — GPU, serves `Qwen3.8-27B` (local weights), internal only.
- **litellm** — the single public LLM entrypoint (host port **4000**).
- **redis** — semantic cache backend.
- **postgres** — persistent LiteLLM metadata / API-key store (host port **5432**).
- **presidio** — PII analyze/anonymize for the LiteLLM pre-call guardrails.
- **user** — web console for token quotas; internal only.
- **nginx** — basic-auth gate, the only public door to the console, served on
  the main domain under the **`/user/`** path (host port **443**).

---

## Phase 0 — Verify / install the host prerequisites

### 0.1 Check the GPU is visible to the OS
```bash
nvidia-smi
```
You should see your GPU. If not, install NVIDIA drivers first (stop here until this works).

### 0.2 Install Docker Engine (if `docker --version` fails)
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER      # run docker without sudo
newgrp docker                       # apply group now (or log out/in)
docker --version
docker compose version
```

### 0.3 Install the NVIDIA Container Toolkit (the GPU↔Docker bridge)
```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### 0.4 PROVE Docker can see the GPU (do not skip)
```bash
docker run --rm --gpus all nvidia/cuda:13.0.0-base-ubuntu22.04 nvidia-smi
```
If your GPU table prints, the host is ready. If you get
`could not select device driver ... [[gpu]]`, step 0.3 didn't take — redo it.

---

## Phase 1 — Assemble the project folder

This runbook assumes the files already live together in one folder (this one).
The layout the compose file expects:

```
Docker/
├── docker-compose.yaml
├── litellm_config.yaml
├── .env                         # secrets (see Phase 2)
├── merge_system.py              # litellm pre-call hook (callbacks:)
├── presidio_server.py           # presidio PII server
├── Dockerfile.presidio
├── requirements.presidio.txt
├── Dockerfile.user
├── user_management_auto/        # user console package
├── nginx/
│   ├── nginx.conf               # basic-auth gate + proxy
│   └── .htpasswd                # pre-generated basic-auth credentials
├── claude.sh                    # convenience launcher for Claude Code
├── loadtest/                    # locust load-test scripts (optional)
└── Qwen3.8-27B/                 # local model weights (mounted read-only)
```

### Model weights — two options
- **Option A (local weights — what the repo ships):** a `Qwen3.8-27B/` folder next
  to the compose file. The compose file mounts it as
  `./Qwen3.8-27B:/Qwen3.8-27B:ro` and passes `--model=/Qwen3.8-27B`.
- **Option B (auto-download, true portability):** change `--model` to a HuggingFace
  repo id and set `HF_TOKEN` in `.env` (the compose already forwards
  `HUGGING_FACE_HUB_TOKEN=${HF_TOKEN:-}`). vLLM downloads on first boot; no local
  weights folder needed. In that case also point the volume at the HF cache.

---

## Phase 2 — Fill in secrets

```bash
cat > .env << 'EOF'
LITELLM_MASTER_KEY=internal-key
HF_TOKEN=
EOF
```

- **`LITELLM_MASTER_KEY`** — used by the `litellm` service, the `user`
  service, and (via its default) the LiteLLM `general_settings.master_key`.
  Set a strong value in production. The compose default fallback is
  `internal-key` if the variable is unset.
- **`HF_TOKEN`** — only needed for Option B (auto-download) or gated models.

> **Note:** the Postgres password is **not** in `.env` — it is hardcoded in
> `docker-compose.yaml` (`POSTGRES_PASSWORD=strong-password`) and must match the
> `DATABASE_URL` in `litellm_config.yaml` / the litellm `DATABASE_URL` env var.
> Change all three places together if you rotate it.

---

## Phase 3 — Validate before running

```bash
docker compose config
```
Prints the fully-resolved config. Any error here (typos, bad indentation, port
mismatch) is caught BEFORE containers start. Fix until it prints clean.

---

## Phase 4 — Build the custom images

Two services are built from local code (`presidio` and `user`):
```bash
docker compose build presidio user
```
(`presidio` needs `Dockerfile.presidio` + `presidio_server.py` + `requirements.presidio.txt`;
`user` needs `Dockerfile.user` + the `user_management_auto/` package.)
If you are not using the console, just build `presidio`.

---

## Phase 5 — Launch the whole stack

```bash
docker compose up -d
```
This pulls the pre-built images (vLLM, LiteLLM, Redis, Postgres, Nginx), builds
the two custom images, starts the private network, mounts volumes, and boots
services in dependency order:

```
vllm-qwen27b ──health─▶ litellm ─▶ user ─▶ nginx
redis, postgres, presidio start alongside (litellm depends_on them)
```

---

## Phase 6 — Watch it come up (27B takes several minutes)

```bash
docker compose ps                        # wait: vllm-qwen27b STATUS = "healthy"
docker compose logs -f vllm-qwen27b      # watch the model load; Ctrl+C to stop watching
```
`litellm` staying in "waiting/created" at first is CORRECT — `depends_on` holds
it until vLLM is healthy, then it starts automatically. `user` and
`nginx` then come up after `litellm`.

Sanity check vLLM directly (optional, internal port):
```bash
docker compose exec litellm curl -s http://vllm-qwen27b:8007/health
```

---

## Phase 7 — Test the full chain (public entrypoint)

LLM endpoint (host port **4000**):
```bash
curl http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer internal-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen27b","messages":[{"role":"user","content":"hello"}]}'
```
A JSON completion = the whole stack works.

User console (served on the main domain under `/user/`, behind basic auth — the
credentials are in `nginx/.htpasswd`):
```bash
curl -u <user>:<password> https://gitaa-ai.tail34d33c.ts.net/user/
```

---

## Phase 8 — Day-to-day lifecycle

| Goal                                   | Command                                   |
|----------------------------------------|-------------------------------------------|
| Start / apply edited compose or config | `docker compose up -d`                    |
| Stop (keep containers)                 | `docker compose stop`                     |
| Stop + remove containers & network     | `docker compose down`                     |
| Restart one service                    | `docker compose restart litellm`          |
| Rebuild after code change              | `docker compose up -d --build presidio user` |
| Status / health                        | `docker compose ps`                       |
| Logs (all / one)                       | `docker compose logs -f [service]`        |
| Live resource use                      | `docker compose stats`                    |
| Shell inside a container               | `docker compose exec litellm sh`          |
| Reset Postgres data (careful)          | `docker compose down -v` then `docker compose up -d` |

---

## Troubleshooting

- **`could not select device driver ... [[gpu]]`** → NVIDIA toolkit not configured; redo Phase 0.3.
- **vLLM exits with `no kernel image is available`** → the pinned vLLM image is too old for your GPU (e.g. Blackwell needs a recent tag + CUDA 13). Use a newer `vllm/vllm-openai` tag. (The repo currently uses `vllm-openai:latest` — pin it.)
- **vLLM OOM on load** → lower `--gpu-memory-utilization` (currently `0.95`) or `--max-model-len` (currently `100000`).
- **`--model` path not found** → the folder mounted into vLLM must match the flag exactly. Here it's `./Qwen3.8-27B` → `--model=/Qwen3.8-27B`.
- **LiteLLM cache errors** → Redis unreachable; confirm the `redis` service is up (`docker compose ps`).
- **LiteLLM errors on key / DB startup** → Postgres down, or the `DATABASE_URL` password doesn't match `POSTGRES_PASSWORD`. Check `docker compose logs postgres litellm`.
- **`callbacks: merge_system.merge_system_instance` fails to load** → `merge_system.py` must be present in the folder and mounted at `/app/merge_system.py` (it is in the compose). A typo in the `callbacks:` line in `litellm_config.yaml` also breaks this.
- **Guardrails (PII) silently missing / 5xx on chat** → `presidio` not up; confirm with `docker compose ps` and `docker compose logs presidio`. The `presidio` guardrails in `litellm_config.yaml` need `http://presidio:5005` reachable.
- **Console gives 401** → wrong basic-auth; the credentials live in `nginx/.htpasswd`.
- **Console can't reach LiteLLM** → `user` must reach `litellm` over the compose network (it sets `LITELLM_URL=http://litellm:5000`). Confirm `litellm` is up.
- **`/user/` returns 404** → the console app isn't up or nginx isn't routing; confirm `user` is running (`docker compose ps`) and that nginx has been restarted after any `nginx.conf` change.
- **Port already in use** → change the left side of `ports:` (host port), e.g. `"5050:5000"`.
- **Presidio / user build fails on COPY** → the source files (`presidio_server.py`, `user_management_auto/`) are missing from the folder.

---

## APPENDIX — file contents

### docker-compose.yaml
Use the version already in this folder. Key points to keep correct:
 - `name: qwen27b` — pinned project name so volumes/network never drift.
 - `image: vllm/vllm-openai:<tag>` — **pin a tag that supports your GPU**
   (the repo currently uses `latest`).
 - `runtime: nvidia` and `ipc: host` on the vLLM service.
 - vLLM volumes: `./Qwen3.8-27B:/Qwen3.8-27B:ro` and `hf-cache`.
 - vLLM has **no `ports:`** on purpose (no real auth — internal only).
 - litellm `ports:` left number (4000) → right number (5000) MUST equal its
   `--port` flag.
 - litellm depends_on vLLM `service_healthy`, and on redis/postgres
   `service_started`.
 - litellm env: `LITELLM_MASTER_KEY`, `PRESIDIO_*_API_BASE` (point at the
   `presidio` service), `DATABASE_URL` (must match Postgres creds).
 - litellm mounts `./litellm_config.yaml` and `./merge_system.py`.
 - Postgres `POSTGRES_PASSWORD` MUST match `DATABASE_URL` (litellm + config).
 - nginx mounts `./nginx/nginx.conf` + `./nginx/.htpasswd`, publishes `443:443`.
   It has one `server` block on the main domain: `/` → litellm, plus `/user/`
   (basic-auth → `user:8080`, prefix stripped).
 - user depends_on litellm; sets `LITELLM_URL`/`MODEL_NAME`/
   `POSTGRES_HOST`/`REDIS_HOST` (service names, not localhost).

### litellm_config.yaml  (DOCKER version — service names, NOT localhost)
```yaml
model_list:
  # 1. Existing local model route
  - model_name: qwen27b
    litellm_params:
      model: hosted_vllm/qwen27b
      api_base: http://vllm-qwen27b:8007/v1
      api_key: "not-needed"
    model_info:
      supports_function_calling: true
      input_cost_per_token: 0.0000001
      output_cost_per_token: 0.0000001

litellm_settings:
  modify_params: true
  num_retries: 3
  request_timeout: 600
  telemetry: false
  callbacks: merge_system.merge_system_instance   # <- pre-call hook (merge_system.py)
  drop_params: true
  set_verbose: true
  cache: true
  cache_params:
    type: "redis"
    host: "redis"        # service name
    port: 6379
    ttl: 3600

router_settings:
  routing_strategy: "least-busy"
  num_retries: 3
  retry_after: 2
  timeout: 600
  allowed_fails: 2
  cooldown_time: 60
  enable_pre_call_checks: true

general_settings:
  master_key: "internal-key"
  database_url: "postgresql://litellm:strong-password@postgres:5432/litellm"
  store_model_in_db: true

guardrails:
  - guardrail_name: "block-cc"
    litellm_params:
      guardrail: presidio
      mode: "pre_call"
      default_on: true
      pii_entities_config:
        CREDIT_CARD: "BLOCK"
  - guardrail_name: "pii-mask"
    litellm_params:
      guardrail: presidio
      mode: "pre_call"
      default_on: true
      pii_entities_config:
        EMAIL_ADDRESS: "MASK"
        PHONE_NUMBER: "MASK"
        US_SSN: "MASK"
```

### requirements.presidio.txt
```
presidio-analyzer==2.2.362
presidio-anonymizer==2.2.362
spacy==3.8.14
Flask==3.1.3
fastapi==0.136.3
starlette==0.46.2
en_core_web_lg @ https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.8.0/en_core_web_lg-3.8.0-py3-none-any.whl
```

### Dockerfile.presidio
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.presidio.txt .
RUN pip install --no-cache-dir -r requirements.presidio.txt
COPY presidio_server.py .
ENV PORT=5005
EXPOSE 5005
CMD ["python", "presidio_server.py"]
```

### Dockerfile.user
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY user_management_auto/ ./user_management_auto/
ENV USER_MANAGEMENT_AUTO_CONFIG=/data/.user_management_auto.json
VOLUME /data
EXPOSE 8080
CMD ["python", "-m", "user_management_auto.server", "--host", "0.0.0.0", "--port", "8080"]
```

---

## The whole happy path, condensed

```bash
# host prep (once)
nvidia-smi
docker run --rm --gpus all nvidia/cuda:13.0.0-base-ubuntu22.04 nvidia-smi

# launch
cd Docker/
docker compose config
docker compose build presidio user
docker compose up -d
docker compose ps                 # wait for vllm-qwen27b "healthy"

# test LLM
curl http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer internal-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen27b","messages":[{"role":"user","content":"hello"}]}'

# test console (basic-auth from nginx/.htpasswd, on the main domain /user/ path)
curl -u <user>:<password> https://gitaa-ai.tail34d33c.ts.net/user/
```
