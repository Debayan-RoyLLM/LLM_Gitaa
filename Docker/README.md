# LLM API Stack

Dockerized internal LLM stack: **vLLM → LiteLLM proxy → Redis/Postgres**, with a **user-management web console** behind an **nginx Basic Auth** gate.

## Services & Ports

| Service            | Port | Purpose                              |
| ------------------ | ---- | ------------------------------------ |
| `litellm`          | 4000 | Public API entrypoint (LiteLLM)      |
| `nginx-auth`       | 8080 | User-management console (auth-gated) |
| `postgres`         | 5432 | LiteLLM metadata store               |
| `redis`            | 6379 | Semantic cache                       |
| `vllm-qwen27b`     | 8007 | Model server (internal only)         |
| `presidio`         | 5005 | PII guardrail (internal only)        |
| `user-management`  | 8080 | Web UI (internal only, via nginx)    |

## Credentials

### 1. Nginx Basic Auth — user-management console (port 8080)

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

- **Files:** `docker-compose.yaml` (lines 79–80, 108) and `litellm_config.yaml` (line 55)
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

### 4. Individual User Tokens (per-user API keys)

Managed through the **user-management web UI** (port 8080, behind Basic Auth) or the
LiteLLM Admin API. Stored in the PostgreSQL database.

## Quick Start

```bash
# First run (creates all containers + volumes)
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
├── merge_system.py              # LiteLLM callback (system message merging)
├── presidio_server.py           # Presidio PII server
├── Dockerfile.presidio
├── Dockerfile.user-management
├── user_management_auto/        # user-management console source
│   ├── config.py
│   ├── html_page.py
│   ├── server.py
│   └── ...
├── nginx/
│   ├── nginx.conf               # Basic Auth + proxy to user-management
│   └── .htpasswd                # Basic Auth credentials
└── loadtest/
    └── locustfile.py            # Locust load-test script
```
