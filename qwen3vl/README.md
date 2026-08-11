# Qwen3-VL-8B-Instruct

Self-contained stack for serving **Qwen3-VL-8B-Instruct** alongside the
existing 35B/9B setup. Nothing outside this folder is modified.

| | Port | Notes |
|---|---|---|
| vLLM (this model) | 8009 | 8007 = qwen35b, 8008 = qwen9b |
| LiteLLM (this model) | 5001 | 5000 = existing proxy |
| GPU | 1 (default) | the 35B already claims 0.80 of GPU 0 |

## Files

| File | Purpose |
|---|---|
| `start_vl.py` | vLLM launcher. All settings from env — nothing hardcoded. |
| `start_vl.sh` | Convenience wrapper with sane defaults. |
| `kill_vl.sh` | Stops **only** this model (matches on `--served-model-name`). |
| `litellm_config_vl.yaml` | LiteLLM config, bare-metal (`localhost:8009`). |
| `litellm_config_vl.docker.yaml` | Same, but `api_base` = compose service name. |
| `docker-compose.vl.yml` | vLLM + LiteLLM as containers. |
| `test_vl.py` | Smoke test: health, models, text, **image**, streaming. |
| `litellm_merge_snippet.yaml` | Paste-in block to serve this model from the *existing* proxy on 5000 instead. |

## One proxy or two?

LiteLLM itself is unchanged either way — same image, same version, config only.

- **Two proxies** (what `docker-compose.vl.yml` does): this model on 5001,
  isolated. But it has its own keys/budgets, so quota accounting is split and
  callers need a second URL.
- **One proxy**: paste `litellm_merge_snippet.yaml` into `../litellm_config.yaml`
  and drop the LiteLLM parts here. Shared keys, budgets and Prometheus; callers
  just change the `"model"` field. Preferred unless you want hard isolation.

## Prerequisites

- **vLLM ≥ 0.11** and **transformers ≥ 4.57**. The architecture
  `Qwen3VLForConditionalGeneration` is unknown to older builds and the server
  will refuse to load the checkpoint.
- Weights at `../models/qwen3-vl-8b-instruct` (bf16 — this is *not* an FP8
  checkpoint like the 35B):
  ```bash
  huggingface-cli download Qwen/Qwen3-VL-8B-Instruct \
      --local-dir ../models/qwen3-vl-8b-instruct
  ```
- **~24 GB VRAM** free: ≈16 GB bf16 weights + vision encoder + KV cache.
  Sharing GPU 0 with the 35B at `0.80` utilization will OOM — use a second
  GPU, or lower utilization on both.

## Run — bare metal

```bash
chmod +x start_vl.sh kill_vl.sh

./start_vl.sh                                 # background
FOREGROUND=1 ./start_vl.sh                    # this terminal

until curl -sf http://localhost:8009/health; do sleep 5; done
python3 test_vl.py

./kill_vl.sh
```

Optional LiteLLM proxy in front:

```bash
litellm --config litellm_config_vl.yaml --port 5001
python3 test_vl.py --base http://localhost:5001 --key internal-key
```

## Run — Docker

```bash
docker compose -f docker-compose.vl.yml -p qwen3vl up -d
docker compose -f docker-compose.vl.yml -p qwen3vl logs -f vllm-qwen3vl8b

python3 test_vl.py --base http://localhost:5001 --key internal-key

docker compose -f docker-compose.vl.yml -p qwen3vl down
```

`-p qwen3vl` keeps this a separate project from the 35B stack so the two never
collide.

## Calling it

```bash
curl http://localhost:5001/v1/chat/completions \
  -H "Authorization: Bearer internal-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3vl8b",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "image_url", "image_url": {"url": "https://example.com/photo.jpg"}},
        {"type": "text", "text": "Describe this image."}
      ]
    }]
  }'
```

`image_url.url` accepts an http(s) URL or a `data:image/png;base64,...` URI.
For local `file://` paths, set `ALLOWED_MEDIA_PATH` — off by default so the
server does not expose its filesystem to callers.

## Flags: why these differ from the 35B

The 35B config is tuned for an **MoE, thinking, FP8** model. This one is
**dense, non-thinking, bf16, multimodal**.

**Removed** — each is a startup failure or silent corruption here:

| Flag | Why it's gone |
|---|---|
| `--moe-backend marlin` | 8B-VL is dense; there are no MoE layers |
| `--speculative-config` (MTP) | Qwen3-VL has no MTP heads |
| `--reasoning-parser qwen3` | Instruct emits no `<think>` blocks. Add it back **only** for `Qwen3-VL-*-Thinking`. |

**Changed:**

| Flag | 35B | Here |
|---|---|---|
| `--tool-call-parser` | `qwen3_coder` | `hermes` — Qwen3-VL emits Hermes-format calls; the coder XML parser silently matches nothing |
| `--max-model-len` | `262144` | `32768` — native is 256K, but on an 8B the KV cache at 256K dwarfs the weights. Raise once you know your VRAM headroom. |
| `--kv-cache-dtype fp8` | on | off — VL quality is more sensitive to it. `KV_CACHE_FP8=1` to re-enable. |
| `--attention-backend flashinfer` | on | off — hard startup failure if the package is missing or the GPU is too old; it does not fall back. `USE_FLASHINFER=1` to enable. |
| `--max-num-seqs` | `512` | `64` — vision prefill is heavy; large batches spike activation memory |

**Added** (multimodal-only, no equivalent in the 35B config):

| Flag | Purpose |
|---|---|
| `--limit-mm-per-prompt` | Hard cap on images/videos per request. Without it, one caller sending 50 images exhausts the context. |
| `--mm-processor-kwargs` (`min_pixels`/`max_pixels`) | The biggest throughput lever. Uncapped, a 4K photo becomes tens of thousands of vision tokens. `1280*28*28` ≈ 1280 tokens/image. |
| `--allowed-local-media-path` | Opt-in local file access. Empty by default. |

## LiteLLM gotchas

- **`model_info.supports_vision: true` is required.** The configs set
  `drop_params: true`; for a model LiteLLM doesn't recognise as multimodal it
  will strip `image_url` parts and return a text-only answer with **no error**.
- **No `cache:` block on purpose.** Base64 images make every request body
  near-unique — hit rate ≈ 0, while each entry costs megabytes of Redis. Enable
  it only if your callers send stable http(s) image URLs.
- `request_timeout` is 300s, not the 35B's 120s. Vision prefill is slow.

## Tuning

All env vars read by `start_vl.py`:

| Var | Default | |
|---|---|---|
| `MODEL_PATH` | — | **required**; local dir or HF repo id |
| `GPU_INDEX` | — | **required** |
| `MODEL_NAME` | `qwen3vl8b` | also the kill-matching key |
| `VLLM_PORT` | `8009` | |
| `MAX_MODEL_LEN` | `32768` | |
| `GPU_MEMORY` | `0.85` | lower if sharing a GPU |
| `DTYPE` | `bfloat16` | |
| `MAX_NUM_SEQS` | `64` | |
| `MAX_NUM_BATCHED_TOKENS` | `16384` | |
| `MAX_IMAGES` / `MAX_VIDEOS` | `4` / `1` | |
| `MIN_PIXELS` / `MAX_PIXELS` | `3136` / `1003520` | drop `MAX_PIXELS` for more speed |
| `ALLOWED_MEDIA_PATH` | *(empty)* | enables `file://` inputs |
| `KV_CACHE_FP8` | `0` | |
| `USE_FLASHINFER` | `0` | |
| `VLLM_API_KEY` | `not-needed` | |

## Not wired up

`../llm_API.py` is **not** integrated with this model. It imports a `config.py`
that does not exist in the repo, and hardcodes upstream ports `8002`/`8003`
([llm_API.py:327-328](../llm_API.py#L327-L328)) matching neither 8007 nor 8009.
Use the LiteLLM proxy on 5001, or fix that file separately.
