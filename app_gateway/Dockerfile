# syntax=docker/dockerfile:1
# Multi-arch: build with  docker buildx build --platform linux/amd64,linux/arm64 ...
# Build stage runs on the HOST's arch (required for cross-arch builds): it
# downloads the Node.js 22 static binary for the TARGET arch via the official
# setup script (no cross-compiled apt packages involved).
FROM --platform=$BUILDPLATFORM python:3.12-slim AS build
ARG TARGETARCH
# curl: also copied to the runtime image (healthcheck + native CLI installers)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    # /usr/bin/npm and npx are symlinks into /usr/lib/node_modules/npm/bin, but
    # COPY --from dereferences symlinks into regular files, which breaks their
    # relative require('../lib/cli.js'). Replace them with absolute-path launchers.
    && rm -f /usr/bin/npm /usr/bin/npx \
    && { echo '#!/bin/sh'; echo 'exec /usr/bin/node /usr/lib/node_modules/npm/bin/npm-cli.js "$@"'; } > /usr/bin/npm \
    && { echo '#!/bin/sh'; echo 'exec /usr/bin/node /usr/lib/node_modules/npm/bin/npx-cli.js "$@"'; } > /usr/bin/npx \
    && chmod +x /usr/bin/npm /usr/bin/npx \
    && node --version && npm --version

FROM python:3.12-slim
WORKDIR /app
# curl for the healthcheck + CLI installs run inside the container
COPY --from=build /usr/bin/curl /usr/bin/curl
# Node.js 22 + npm — so the "via npm" install buttons work inside the container.
# npm/npx are symlinks into /usr/lib/node_modules, so copy that tree + the shims.
COPY --from=build /usr/bin/node /usr/bin/node
COPY --from=build /usr/lib/node_modules /usr/lib/node_modules
COPY --from=build /usr/bin/npm /usr/bin/npm
COPY --from=build /usr/bin/npx /usr/bin/npx
COPY llm_gateway_setup/ ./llm_gateway_setup/
COPY llm-gateway-setup.py .

ENV PATH="/root/.local/bin:${PATH}" \
    PORT=8765

EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s --retries=5 \
    CMD curl -sf http://localhost:8765/ || exit 1

CMD ["python", "llm-gateway-setup.py", "--host", "0.0.0.0", "--port", "8765"]
