# Build the static frontend with an immutable Linux/amd64 base image.
FROM node:22-alpine@sha256:c610fcdfb1d5b4740dd70c284ed3cb16bb857e0f7166196e36a5501df7a3aa32 AS frontend-build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Fetch scanner release artifacts without executing upstream installer scripts.
FROM python:3.12-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea AS scanner-download
ARG TARGETARCH
ARG OPENGREP_VERSION=1.23.0
ARG OPENGREP_SHA256=1f06548af379ab6080698a609612890ffad2d92dc2172f1e97d38d48096d5ef8
ARG TRIVY_VERSION=0.71.2
ARG TRIVY_SHA256=0510e71e2fd39bf863856d499c8dc19feb4e7336546394c502a8f5cc7ab27460
WORKDIR /build
COPY docker/install_scanners.py ./
RUN test "${TARGETARCH}" = "amd64" \
    && python install_scanners.py \
    --output /tools \
    --opengrep-version "${OPENGREP_VERSION}" \
    --opengrep-sha256 "${OPENGREP_SHA256}" \
    --trivy-version "${TRIVY_VERSION}" \
    --trivy-sha256 "${TRIVY_SHA256}"

# Resolve the locked Python environment in a disposable build stage.
FROM python:3.12-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea AS backend-build
ARG UV_VERSION=0.10.10
WORKDIR /app
RUN python -m pip install --no-cache-dir "uv==${UV_VERSION}"
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Production image contains only the application, locked environment, and scanners.
FROM python:3.12-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea

ENV HOME=/home/app \
    PATH=/app/.venv/bin:/usr/local/bin:/usr/bin:/bin \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TRIVY_CACHE_DIR=/home/app/.cache/trivy

WORKDIR /app

RUN printf '%s\n' 'app:x:10001:' >> /etc/group \
    && printf '%s\n' 'app:x:10001:10001:Application user:/home/app:/usr/sbin/nologin' >> /etc/passwd \
    && mkdir -p /home/app/.cache/trivy /home/app/.opengrep \
    && chown -R 10001:10001 /home/app

COPY --from=scanner-download /tools/opengrep /usr/local/bin/opengrep
COPY --from=scanner-download /tools/trivy /usr/local/bin/trivy
COPY --from=backend-build /app/.venv /app/.venv
COPY backend/ ./
COPY --from=frontend-build /app/out ./static

USER 10001:10001

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5)"]

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
