# LLM Gateway Setup — Docker

Web UI for configuring **Claude Code** and **Qwen Code** against an internal
LiteLLM gateway. Enter the gateway address + API key once; the app writes the
config into the container's home and can install both CLIs right from the page.

No third-party Python dependencies — the stock `python:3.12-slim` image is the
whole runtime, so the image is small (~45 MB) and needs no `pip install`.

## Run

```bash
docker run -d --name llm-gateway-setup \
  -p 8765:8765 \
  -v gw-setup-data:/root \
  --restart unless-stopped \
  llm-gateway-setup:latest
```

Then open **http://localhost:8765** in a browser.

- `-v gw-setup-data:/root` — persists everything (`~/.claude`, `~/.qwen`,
  `~/.config/internal-llm`, installed CLIs) across container upgrades.
  Drop the volume flag to run it fully stateless.
- Any exposed port works, e.g. `-p 9000:8765` (the container always listens
  on 8765).

## Access from another machine

The server binds `0.0.0.0` inside the container, so on a host with a LAN IP
or Tailscale address, `http://<host-ip>:8765` just works. The UI authenticates
API calls with a random token embedded in the page on each startup, so no
additional auth is needed for internal use.

For an HTTPS endpoint in front, point a reverse proxy at port 8765.

## Build from source

```bash
# single arch
docker build -t llm-gateway-setup:latest .

# multi-arch (amd64 + arm64), e.g. for pushing to a registry
docker buildx build --platform linux/amd64,linux/arm64 \
  -t <registry>/llm-gateway-setup:latest --push .
```

## What the container can do

| Action | Where it lands (inside the container) |
|---|---|
| Test gateway connection | outbound HTTPS to *your* LiteLLM gateway |
| Save config | `/root/.config/internal-llm/env`, `/root/.claude/settings.json`, `/root/.qwen/.env` |
| Install Claude Code / Qwen Code | `claude` / `qwen` binaries, ready in the container's `PATH` |

To use a CLI configured this way:

```bash
docker exec -it llm-gateway-setup bash -lc 'claude'   # or: qwen
```
