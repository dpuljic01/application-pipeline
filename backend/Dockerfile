# --- Stage 1: "poetry" — install dependencies into a virtualenv, nothing else ---
FROM python:3.11-slim AS poetry

# pinned to match the Poetry version that actually generated poetry.lock (2.3.1) —
ENV POETRY_VERSION=2.3.1
# Poetry's own installation lives here, isolated from the project's dependencies
ENV POETRY_HOME=/opt/poetry
# force the project's virtualenv into a fixed, known path (/app/.venv) instead of a
# hash-named folder under a shared venv directory — makes it easier to COPY it later
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV PATH="/opt/poetry/bin:$PATH"

# install Poetry itself into its own venv, kept separate from the app's dependencies
RUN python -m venv "$POETRY_HOME" \
	&& "$POETRY_HOME/bin/pip" install --no-cache-dir "poetry==$POETRY_VERSION"

WORKDIR /app
# copy only the dependency manifests first, not the app code — Docker caches each
# layer, so this layer (and the slow `poetry install` below) is reused on rebuilds
COPY pyproject.toml poetry.lock* ./
# --only main: skip the dev group — not needed at runtime
# --no-root: package-mode = false in pyproject.toml, there's no local package to install
RUN poetry install --only main --no-root --no-interaction --no-ansi

# --- Stage 2: "runtime" — just the venv + app code, no Poetry, no dev tools ---
FROM python:3.11-slim AS runtime

# put the venv's binaries first on PATH so `uvicorn`, `python`, etc. resolve to the
# versions installed inside it, not the system Python
ENV PATH="/app/.venv/bin:$PATH"
# write logs straight through instead of buffering
ENV PYTHONUNBUFFERED=1
# skip writing .pyc bytecode files — they're not needed in a container and just take up space
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
# take only finished virtualenv from the builder stage — Poetry and every tool it needed, never makes it into this final image
COPY --from=poetry /app/.venv /app/.venv
COPY . .

EXPOSE 8000

# must bind 0.0.0.0, not uvicorn's default 127.0.0.1 — otherwise the process only accepts
# connections from inside its own container, and the ALB / ECS health check could never reach it
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
