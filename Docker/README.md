# LLM API Stack

Dockerized internal LLM stack: **vLLM → LiteLLM proxy → Redis/Postgres**, with a **user-management web console** behind an **nginx Basic Auth** gate and an **Open WebUI** chat interface behind the same TLS proxy. All external traffic enters over HTTPS through nginx.

For architecture diagrams and request lifecycle see [arch.md](arch.md); for setup, troubleshooting, and day-to-day operations see [RUNBOOK.md](RUNBOOK.md).

## Services & Ports

| Service            | Image                          | External port | Internal port | Purpose                                      |
| ------------------ | ------------------------------ | ------------- | ------------- | -------------------------------------------- |
| `litellm`          | `ghcr.io/berriai/litellm`      | 4000*         | 5000          | LLM gateway: auth, routing, cache, PII       |
| `nginx`            | `nginx:1.27-alpine`            | **443**       | 443           | TLS termination, reverse proxy, HSTS         |
| `open-webui`       | `ghcr.io/open-webui/open-webui`| **3000**      | 8080          | Chat UI (RAG, document upload)               |
| `user`             | built from `Dockerfile.user`   | — (via 443)   | 8080          | User-management console (Basic Auth gated)   |
| `postgres`         | `postgres:15-alpine`           | 5432          | 5432          | LiteLLM metadata store (keys, spend)         |
| `redis`            | `redis:7-alpine`               | —             | 6379          | Semantic cache (1 h TTL)                     |
| `vllm-qwen27b`     | `vllm/vllm-openai`             | —             | 8007          | Model server (Qwen3.8-27B, GPU, fp8)         |
| `presidio`         | built from `Dockerfile.presidio` | —           | 5005          | PII analyzer/anonymizer (guardrail)          |

\* `4000:5000` is still mapped in `docker-compose.yaml` for local/debug access, but the
intended public door for the LLM API is **443 only** (nginx → litellm). Remove the 4000
mapping if you want TLS to be the sole entry point.

## Credentials

### 1. Nginx Basic Auth — user-management console (port 443, path `/user/`)

The only public door to the user-management web UI.

- **File:** `nginx/.htpasswd`
- **Current user:** `Sundar` (change it below)

#### How to change

```bash
# Install htpasswd if missing
sudo apt install apache2-utils

# Create a new entry (prompts for password twice)
htpasswd -c /home/gitaa/Desktop/LLM_API/Docker/nginx/.htpasswd newusername

# Restart nginx to pick up the new file
cd /home/gitaa/Desktop/LLM_API/Docker
docker compose restart nginx
```

### 2. LiteLLM Master Key — API access

Used as the `Authorization: Bearer <key>` header for all LiteLLM requests.

- **File:** `litellm_config.yaml` → `general_settings.master_key`
- **Override via env:** `LITELLM_MASTER_KEY` in `.env` (takes precedence in `docker-compose.yaml`)

#### How to change

```yaml
# litellm_config.yaml
general_settings:
  master_key: "your-new-master-key"
```

```bash
docker compose restart litellm
```

### 3. PostgreSQL — LiteLLM database

- **Files:** `docker-compose.yaml` (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_URL`) and `litellm_config.yaml` (`database_url`)
- **Default:** user `litellm`, password `strong-password`, db `litellm`

#### How to change

Update **all three** occurrences to the same new value:

| File                   | Key / Line       |
| ---------------------- | ---------------- |
| `docker-compose.yaml`  | `POSTGRES_USER`  |
| `docker-compose.yaml`  | `POSTGRES_PASSWORD` |
| `docker-compose.yaml`  | `DATABASE_URL`   |
| `litellm_config.yaml`  | `database_url`   |

> **Warning:** Changing Postgres credentials after the `postgres-data` volume is already
> created has no effect — the initial user is baked in at first container start.
> To truly change them you must either:
>
> 1. **Remove the volume** and re-create the DB (all data is lost), **or**
> 2. Connect to the running DB and create a new role, then update the config.

### 4. Open WebUI — chat UI (port 3000)

- **Env:** `OPENWEBUI_LITELLM_KEY` in `.env` (defaults to `internal-key` — the LiteLLM master key)
- **WebUI secret:** `WEBUI_SECRET_KEY` in `.env` (set a strong value in production)
- **WebUI URL:** hardcoded in `docker-compose.yaml` as `https://gitaa-ai.tail34d33c.ts.net:3000`

### 5. Individual User Tokens (per-user API keys)

Managed through the **user-management web UI** (port 443, path `/user/`, behind Basic Auth)
or the LiteLLM Admin API. Stored in the PostgreSQL database.

## Quick Start

```bash
# First run (creates all containers + volumes, builds custom images)
docker compose up -d

# Check health
docker compose ps

# Stop everything
docker compose down

# Stop and remove volumes (destructive!)
docker compose down -v
```

## File Map

```
Docker/
├── docker-compose.yaml          # all services
├── litellm_config.yaml          # LiteLLM models, cache, DB, guardrails
├── .env                         # secrets (LITELLM_MASTER_KEY, HF_TOKEN, etc.)
├── merge_system.py              # LiteLLM callback (system message merging)
├── presidio_server.py           # Presidio PII server
├── requirements.presidio.txt    # Presidio Python dependencies
├── Dockerfile.presidio          # Presidio image
├── Dockerfile.user              # User-management console image
├── user_management_auto/        # user-management console source (stdlib http.server)
│   ├── __init__.py
│   ├── config.py
│   ├── api.py
│   ├── html_page.py
│   ├── server.py
│   └── wipe_users.py
├── nginx/
│   ├── nginx.conf               # TLS + reverse proxy (443: / → litellm, /user/ → user; 3000: / → open-webui)
│   ├── .htpasswd                # Basic Auth credentials
│   └── certs/                   # TLS certificates (mounted read-only)
├── claude.sh                    # convenience launcher for Claude Code
├── loadtest/
│   ├── locustfile.py            # Locust load-test script
│   ├── run.sh                   # helper runner
│   └── results_*.csv            # past load-test results
├── arch.md                      # architecture diagrams & request lifecycle
└── RUNBOOK.md                   # setup, troubleshooting, day-to-day ops
```
