# Runbook — Dockerized vLLM + LiteLLM + Redis stack (from scratch)

Follow this on a machine where you have **root + a real Docker daemon + an NVIDIA GPU**
(a plain GPU VM or a privileged pod — NOT an unprivileged managed pod).

Stack: `vllm-qwen35b` (GPU) → `litellm` (proxy, public) → `redis` (cache), plus optional `presidio`.

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

```bash
mkdir -p ~/llm-stack && cd ~/llm-stack
```

Put these files in this folder (contents in the Appendix below):
```
llm-stack/
├── docker-compose.yml
├── litellm_config.yaml
├── .env
├── Dockerfile.presidio          # optional (presidio)
├── requirements.presidio.txt    # optional (presidio)
├── presidio_server.py           # optional (presidio) — YOUR script
└── models/                      # your weights, OR use a HuggingFace ID (see note)
```

### Model weights — two options
- **Option A (local weights):** copy your `models/qwen3.6-35b-a3b-fp8/` folder here.
  Keep `--model=/models/qwen3.6-35b-a3b-fp8` in the compose file.
- **Option B (auto-download, true portability):** change that flag to a HuggingFace
  repo id, e.g. `--model=Qwen/Qwen3-30B-A3B`, and set `HF_TOKEN` in `.env`.
  vLLM downloads on first boot; no `models/` folder needed.

---

## Phase 2 — Fill in secrets

```bash
cat > .env << 'EOF'
LITELLM_MASTER_KEY=internal-key
HF_TOKEN=
EOF
```
(Set a strong key in production; add HF_TOKEN only if using Option B or gated models.)

---

## Phase 3 — Validate before running

```bash
docker compose config
```
Prints the fully-resolved config. Any error here (typos, bad indentation, port
mismatch) is caught BEFORE containers start. Fix until it prints clean.

---

## Phase 4 — Build the one custom image (presidio only)

Skip this whole phase if you are not using presidio.
```bash
# make sure the filename matches EXACTLY (capital D, "presidio"):
mv dockerfile.presido Dockerfile.presidio 2>/dev/null || true
docker compose build presidio
```

---

## Phase 5 — Launch the whole stack

```bash
docker compose up -d
```
This pulls the pre-built images (vLLM, LiteLLM, Redis), starts the private
network, mounts volumes, and boots services in dependency order.

---

## Phase 6 — Watch it come up (35B takes several minutes)

```bash
docker compose ps                       # wait: vllm-qwen35b STATUS = "healthy"
docker compose logs -f vllm-qwen35b     # watch the model load; Ctrl+C to stop watching
```
`litellm` staying in "waiting/created" at first is CORRECT — `depends_on` holds
it until vLLM is healthy, then it starts automatically.

Sanity check vLLM directly (optional, internal port):
```bash
docker compose exec litellm curl -s http://vllm-qwen35b:8007/health
```

---

## Phase 7 — Test the full chain (public entrypoint)

```bash
curl http://localhost:5000/v1/chat/completions \
  -H "Authorization: Bearer internal-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen35b","messages":[{"role":"user","content":"hello"}]}'
```
A JSON completion = the whole stack works.
(Use the port that matches your compose `ports:` — 5000 or 4000.)

---

## Phase 8 — Day-to-day lifecycle

| Goal                                   | Command                                   |
|----------------------------------------|-------------------------------------------|
| Start / apply edited compose or config | `docker compose up -d`                    |
| Stop (keep containers)                 | `docker compose stop`                     |
| Stop + remove containers & network     | `docker compose down`                     |
| Restart one service                    | `docker compose restart litellm`          |
| Rebuild presidio after code change     | `docker compose up -d --build`            |
| Status / health                        | `docker compose ps`                       |
| Logs (all / one)                       | `docker compose logs -f [service]`        |
| Live resource use                      | `docker compose stats`                    |
| Shell inside a container               | `docker compose exec litellm sh`          |

---

## Troubleshooting

- **`could not select device driver ... [[gpu]]`** → NVIDIA toolkit not configured; redo Phase 0.3.
- **vLLM exits with `no kernel image is available`** → the pinned vLLM image is too old for your GPU (e.g. Blackwell needs a recent tag + CUDA 13). Use a newer `vllm/vllm-openai` tag.
- **vLLM OOM on load** → lower `--gpu-memory-utilization` or `--max-model-len`.
- **`--model` path not found** → the folder name under `models/` must match the flag exactly.
- **LiteLLM cache errors** → Redis unreachable; confirm the `redis` service is up (`docker compose ps`).
- **Port already in use** → change the left side of `ports:` (host port), e.g. `"5050:5000"`.
- **Presidio build fails on COPY** → `presidio_server.py` is missing from the folder.

---

## APPENDIX — file contents

### docker-compose.yml
(Use the version already in your folder. Key points to keep correct:
 - `image: vllm/vllm-openai:<tag>`  — pin a tag that supports your GPU
 - `runtime: nvidia` and `ipc: host` on the vLLM service
 - volumes: `./models:/models:ro`
 - litellm `ports:` left number MUST equal litellm `--port`
 - litellm depends_on vLLM `service_healthy`)

### litellm_config.yaml  (DOCKER version — service names, NOT localhost)
```yaml
model_list:
  - model_name: qwen35b
    litellm_params:
      model: openai/qwen35b
      api_base: http://vllm-qwen35b:8007/v1   # service name, not localhost
      api_key: "not-needed"
      stream: true

litellm_settings:
  num_retries: 3
  request_timeout: 120
  drop_params: true

cache:
  type: "redis"
  host: "redis"        # service name
  port: 6379
  ttl: 3600

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
```

### requirements.presidio.txt
```
presidio-analyzer==2.2.362
presidio-anonymizer==2.2.362
spacy==3.8.14
Flask==3.1.3
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

---

## The whole happy path, condensed

```bash
# host prep (once)
nvidia-smi
docker run --rm --gpus all nvidia/cuda:13.0.0-base-ubuntu22.04 nvidia-smi

# launch
cd ~/llm-stack
docker compose config
docker compose build presidio     # if using presidio
docker compose up -d
docker compose ps                 # wait for "healthy"

# test
curl http://localhost:5000/v1/chat/completions \
  -H "Authorization: Bearer internal-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen35b","messages":[{"role":"user","content":"hello"}]}'
```
