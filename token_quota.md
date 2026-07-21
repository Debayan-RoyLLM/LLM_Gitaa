# Working Runbook — Native vLLM + LiteLLM + Postgres stack with per-user token quotas

Environment: NeevCloud pod (no systemd, no Docker), files under `/data`.
Everything runs natively (no containers). Nothing auto-starts — after any pod
restart, repeat Phase 2.

---

## PHASE 1 — One-time setup (do once)

### 1.1 Install & start PostgreSQL
```bash
apt update && apt install -y postgresql postgresql-contrib
ls /usr/lib/postgresql/                 # note the version (e.g. 16)
pg_ctlcluster 16 main start             # manual start (no systemd here)
sudo -u postgres psql -c "SELECT version();"   # confirm it's up
```
Function: Postgres is the database that stores users, API keys, and per-user
spend. LiteLLM needs it for quota tracking. `pg_ctlcluster` is the no-systemd
way to start it.

### 1.2 Create LiteLLM's database and user
```bash
sudo -u postgres psql -c "CREATE USER litellm WITH PASSWORD 'strong-password';"
sudo -u postgres psql -c "CREATE DATABASE litellm OWNER litellm;"
```
Function: gives LiteLLM its own login and database to write to.

### 1.3 Generate the Prisma client (LiteLLM's DB layer)
```bash
prisma generate --schema /data/envs/qwen3-vllm/lib/python3.11/site-packages/litellm/proxy/schema.prisma
```
Function: LiteLLM talks to Postgres through Prisma. Prisma needs its client
binaries generated once from LiteLLM's bundled schema, or LiteLLM crashes at
startup with "Unable to find Prisma binaries."

### 1.4 Point LiteLLM at the database (edit litellm_config.yaml)
```yaml
general_settings:
  master_key: "internal-key"
  database_url: "postgresql://litellm:strong-password@localhost:5432/litellm"
  store_model_in_db: true
```
Function: tells LiteLLM where the database is. Note `localhost` (native mode),
NOT a container name.

### 1.5 Set per-token cost so tokens convert to budget (edit litellm_config.yaml)
```yaml
model_list:
  - model_name: qwen35b
    litellm_params:
      model: openai/qwen35b
      api_base: http://localhost:8007/v1
      api_key: "not-needed"
      input_cost_per_token: 0.0000001
      output_cost_per_token: 0.0000001
      stream: true
```
Function: quotas are enforced in DOLLARS. This cost rate converts tokens → spend.
At 0.0000001/token: $1.00 budget = 10,000,000 tokens/month.
CRITICAL: without these lines, spend always = 0 and the quota never enforces.
CRITICAL: indentation is spaces only, children indented more than parents.

### 1.6 Validate the config before starting
```bash
python3 -c "import yaml; yaml.safe_load(open('/data/litellm_config.yaml')); print('YAML OK')"
```
Function: catches indentation/syntax errors before launch. Must print "YAML OK".

---

## PHASE 2 — Start the stack (repeat after every pod restart)

Order matters: database → cache → model server → proxy.

### 2.1 Start Postgres
```bash
pg_ctlcluster 16 main start
```

### 2.2 Start Redis (LiteLLM's cache)
```bash
redis-server --daemonize yes && redis-cli ping     # expect PONG
```
Function: Redis caches responses so repeated questions skip the GPU. Optional
but configured; LiteLLM's cache block points at localhost:6379.

### 2.3 Start vLLM (the model server, on the GPU)
```bash
cd /data
MODEL_NAME=qwen35b MODEL_PATH=models/qwen3.6-35b-a3b-fp8 GPU_INDEX=0 \
  nohup python3 start_model.py > vllm.log 2>&1 &
```
Function: loads Qwen 35B onto the GPU and serves an OpenAI-compatible API on
port 8007. Takes several minutes for a 35B model.

### 2.4 Wait until vLLM is ready
```bash
until curl -sf http://localhost:8007/health >/dev/null; do echo "loading..."; sleep 5; done
echo "vLLM ready"
```
Function: LiteLLM needs vLLM up before it can route to it. This blocks until
vLLM's /health returns OK.

### 2.5 Start LiteLLM (the proxy / front door)
```bash
cd /data
python3 start_litellm.py
```
Function: starts the proxy on port 4000. It connects to Postgres, auto-creates
its tables on first run, applies auth (master key + per-user keys), routing,
caching, and quota enforcement. This is the endpoint users actually call.

---

## PHASE 3 — Manage users & quotas (day-to-day)

### 3.1 Create a user with a monthly-resetting token quota
```bash
curl -X POST 'http://localhost:4000/key/generate' \
  -H 'Authorization: Bearer internal-key' \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"NAME","max_budget":1.0,"budget_duration":"30d","models":["qwen35b"]}'
```
Function: creates an API key tied to a user with a monthly quota.
- max_budget 1.0 + cost 0.0000001 = 10,000,000 tokens/month
- budget_duration "30d" = auto-resets every 30 days
Returns "key":"sk-..." — give THAT to the user as their API key.

### 3.2 The user makes requests with THEIR key
```bash
curl http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-THEIR-KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen35b","messages":[{"role":"user","content":"hello"}]}'
```
Function: normal chat call. LiteLLM logs their tokens, adds to their spend, and
rejects them automatically once they exceed max_budget (until the 30-day reset).

### 3.3 Check a user's usage
```bash
curl -X GET 'http://localhost:4000/key/info?key=sk-THEIR-KEY' \
  -H 'Authorization: Bearer internal-key'
```
Function: shows their running "spend" vs "max_budget" and "budget_reset_at".

### 3.4 Change a user's quota
```bash
curl -X POST 'http://localhost:4000/key/update' \
  -H 'Authorization: Bearer internal-key' -H 'Content-Type: application/json' \
  -d '{"key":"sk-THEIR-KEY","max_budget":5.0}'
```
Function: raise/lower an existing key's budget without recreating it.

### 3.5 Revoke a user
```bash
curl -X POST 'http://localhost:4000/key/delete' \
  -H 'Authorization: Bearer internal-key' -H 'Content-Type: application/json' \
  -d '{"keys":["sk-THEIR-KEY"]}'
```
Function: disables that key immediately.

---

## PHASE 4 — Inspect usage in the database (tables)

### 4.1 Per-request token log (audit trail, one row per request)
```bash
sudo -u postgres psql -d litellm -c \
'SELECT "user", model, prompt_tokens, completion_tokens, total_tokens, spend, "startTime" FROM "LiteLLM_SpendLogs" ORDER BY "startTime" DESC LIMIT 10;'
```
Function: every request with its exact token counts and computed spend.

### 4.2 Per-user totals (one row per user)
```bash
sudo -u postgres psql -d litellm -c \
'SELECT "user", COUNT(*) AS requests, SUM(total_tokens) AS tokens, SUM(spend) AS total_spend FROM "LiteLLM_SpendLogs" GROUP BY "user";'
```
Function: aggregated usage per person.

### 4.3 Web dashboard (if port 4000 is reachable from a browser)
```
http://<host>:4000/ui        (log in with master key)
```
Function: same data as tables, in a UI.

---

## PHASE 5 — Reset / cleanup

### Delete a single user's data
```bash
curl -X POST 'http://localhost:4000/user/delete' \
  -H 'Authorization: Bearer internal-key' -H 'Content-Type: application/json' \
  -d '{"user_ids":["NAME"]}'
sudo -u postgres psql -d litellm -c "DELETE FROM \"LiteLLM_SpendLogs\" WHERE \"user\" = 'NAME';"
```

### Full wipe (all users, keys, logs)
```bash
sudo -u postgres psql -d litellm -c \
'TRUNCATE "LiteLLM_SpendLogs", "LiteLLM_VerificationToken", "LiteLLM_UserTable" CASCADE;'
```

---

## IMPORTANT — persistence & restart caveats

1. NO SYSTEMD: nothing auto-starts. After any pod restart, redo all of PHASE 2.
   Save a start_all.sh (below) so it's one command.

2. DATA PERSISTENCE: all users/keys/spend live in Postgres. Confirm its data
   directory is on a PERSISTENT mount, or a pod restart wipes everything:
   ```bash
   df -h /var/lib/postgresql/16/main && mount | grep -E "overlay|/data"
   ```
   If it shows "overlay" (not /data), relocate Postgres data onto /data:
   ```bash
   pg_ctlcluster 16 main stop
   sudo -u postgres /usr/lib/postgresql/16/bin/initdb -D /data/pgdata
   sudo -u postgres /usr/lib/postgresql/16/bin/pg_ctl -D /data/pgdata -l /data/pgdata/logfile start
   # then recreate the litellm user/db (steps 1.2) against this instance
   ```

3. NATIVE-MODE CONFIG: api_base, cache host, and database_url must all use
   "localhost" — NOT container/service names.

---

## start_all.sh — one-command restart recovery

```bash
#!/bin/bash
set -e
pg_ctlcluster 16 main start || true
redis-server --daemonize yes
cd /data
MODEL_NAME=qwen35b MODEL_PATH=models/qwen3.6-35b-a3b-fp8 GPU_INDEX=0 \
  nohup python3 start_model.py > vllm.log 2>&1 &
echo "Waiting for vLLM..."
until curl -sf http://localhost:8007/health >/dev/null; do sleep 5; done
echo "vLLM up. Starting LiteLLM..."
python3 start_litellm.py
```
