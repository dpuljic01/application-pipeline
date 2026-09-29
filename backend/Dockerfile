# --- Stage 1: "builder" — install dependencies into a virtualenv, nothing else ---
FROM python:3.11-slim AS builder

# uv is a single static binary — copy it in from the official image instead of
# pip-installing a package manager. Pinned to the version that generated uv.lock.
COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /bin/uv

# compile .pyc at install time so the first request doesn't pay for it; copy
# files into the venv instead of hardlinking (the uv cache mount below is a
# different filesystem, so hardlinks would fail anyway)
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
# use the image's Python, never download a managed one
ENV UV_PYTHON_DOWNLOADS=never

WORKDIR /app
# copy only the dependency manifests first, not the app code — Docker caches each
# layer, so this layer (and the slow install below) is reused on rebuilds
COPY pyproject.toml uv.lock ./
# --frozen: install exactly what uv.lock says, fail instead of re-resolving
# --no-dev: skip the dev group — not needed at runtime
# the cache mount keeps downloaded wheels between builds without baking them into a layer
RUN --mount=type=cache,target=/root/.cache/uv \
	uv sync --frozen --no-dev

# --- Stage 2: "runtime" — just the venv + app code, no uv, no dev tools ---
FROM python:3.11-slim AS runtime

# put the venv's binaries first on PATH so `uvicorn`, `alembic`, etc. resolve to the
# versions installed inside it, not the system Python
ENV PATH="/app/.venv/bin:$PATH"
# write logs straight through instead of buffering
ENV PYTHONUNBUFFERED=1
# skip writing .pyc bytecode files at runtime — they were already compiled at build time
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
# take only the finished virtualenv from the builder stage — uv never makes it into this final image
COPY --from=builder /app/.venv /app/.venv
COPY . .

EXPOSE 8000

# Run migrations before starting the server, so code never ships ahead of its
# schema (Render doesn't run migrations on deploy — this caused two prod outages).
# `&&` means a failed migration exits the container instead of serving a broken
# app; the platform's health check then fails the deploy and keeps the old one live.
# `exec` replaces the shell with uvicorn so it receives SIGTERM directly on shutdown.
# Safe with one instance; with several replicas starting at once, move this to a
# one-off task before the rollout instead (alembic has no cross-process lock).
#
# must bind 0.0.0.0, not uvicorn's default 127.0.0.1 — otherwise the process only accepts
# connections from inside its own container, and the platform's health check could never reach it
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
