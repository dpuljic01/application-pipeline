# Application Pipeline

**Application Pipeline** is a lightweight, CRM‑style web application that turns a chaotic job search into a **clear, measurable pipeline**.

It is designed both as:

* a **real tool** you can use daily, and
* an **interview‑ready portfolio project** demonstrating clean architecture, AWS, and modern backend practices.

---

## Problem

Most job searches fail due to:

* inconsistent applications
* forgotten follow‑ups
* lost documents and links
* zero feedback loops (no idea what works)

Spreadsheets and Notion break down as volume increases.

**Application Pipeline** fixes this by treating a job search like a real sales pipeline.

---

## Solution

A simple, focused system to:

* track applications and outreach
* enforce clear stages and transitions
* centralize documents and notes
* enable reminders and follow‑ups
* surface patterns over time

Single‑user first. Designed for multi‑user later.

---

## Core Concepts

* Modular monolith (clean, scalable, interview‑friendly)
* Strong separation of concerns (API / Services / Domain / DB)
* AWS‑native authentication (Cognito)
* UUID‑based public identifiers
* Explicit dependency injection

See **`docs/application-pipeline-cheat-sheet.md`** for detailed architectural notes.

---

## 🏗️ Architecture Overview

```
frontend/        # Next.js (minimal auth + UI)
backend/
  api/           # FastAPI routers (HTTP only)
  services/      # Business logic
  domain/        # Core models & rules (framework‑free)
  db/            # SQLAlchemy models & repositories
  integrations/  # AWS / external services
  core/          # config, logging, shared utilities
infra/           # Terraform / IaC (later)
docs/            # Architecture & design notes
```

**Why a modular monolith?**

* Faster iteration than microservices
* Easier testing
* Clear mental model
* Can be split later if needed

---

## 🔐 Authentication

* AWS Cognito User Pool
* OAuth2 Authorization Code Flow
* JWT verification on backend
* `/me` endpoint to map Cognito users → internal users

Backend **never** trusts frontend claims.

---

## 🧪 Tech Stack

### Backend

* Python 3.11+
* FastAPI
* SQLAlchemy
* PostgreSQL
* AWS Cognito
* Docker

### Frontend (planned)

* Next.js
* TypeScript
* shadcn/ui

### Infrastructure (planned)

* AWS ECS (Fargate)
* RDS PostgreSQL
* S3
* EventBridge

---

## Getting Started (Local)

### Prerequisites

* Docker Desktop (runs Postgres)
* Python 3.11+
* [Poetry](https://python-poetry.org/) for dependency management

### Backend

```bash
cd backend

# 1. Start Postgres
docker compose up -d

# 2. Configure environment
cp .env.example .env
# then fill in COGNITO_REGION / COGNITO_USER_POOL_ID / COGNITO_APP_CLIENT_ID

# 3. Install dependencies
poetry install

# 4. Run database migrations
poetry run alembic upgrade head

# 5. Start the API
poetry run uvicorn app.main:app --reload
```

The API is now running at `http://localhost:8000` (interactive docs at `/docs`). Confirm it's talking to Postgres:

```bash
curl http://localhost:8000/api/health
# {"status": "ok", "db": true}
```

### Running Tests

```bash
cd backend
poetry run pytest
```

Tests run against the same local Postgres instance — each test runs inside a transaction that's rolled back at teardown, so nothing persists and no separate test database is needed. Full suite runs in well under a second.

### Lint & Format

```bash
cd backend
poetry run ruff check . --fix
poetry run ruff format .
```

A pre-commit hook runs both automatically on every commit. Enable it once per clone with `poetry run pre-commit install` (from `backend/`).

### CI

Every push and pull request runs `.github/workflows/ci.yml`: lint, format check, migrations, and the full test suite against a real `postgres:16` service container.

### Troubleshooting

* **`docker compose up -d` runs but the app seems to hit a different/empty database, or migrations behave unexpectedly**: something else may already be bound to port 5432 (a native Postgres install, another project's container). Check with `lsof -iTCP:5432 -sTCP:LISTEN` — if a non-Docker `postgres` process shows up, stop it before starting this project's container so you're not silently talking to the wrong database.
* **`alembic upgrade head` fails with a role/database "does not exist" error**: the Docker volume may have been initialized under different Postgres credentials than what's currently in `docker-compose.yml`/`.env` (Postgres only applies `POSTGRES_USER`/`POSTGRES_DB` env vars the *first* time a volume is initialized). Either match `.env` to what the volume actually has, or remove the `db_data` volume to reinitialize from scratch (this deletes local dev data).

### Frontend (planned)

```bash
cd frontend
npm install
npm run dev
```

Environment variables are required for Cognito and DB access.

---

## Design Principles

* Explicit > implicit
* Boring tech > clever abstractions
* Business logic isolated from frameworks
* Every layer has one responsibility

If a piece of code is hard to explain, it’s probably in the wrong layer.

---

## Documentation

* `docs/application-pipeline-cheat-sheet.md` – core concepts & mental models
* More docs will be added as features grow

---

## Why This Project Matters

This project is intentionally designed to demonstrate:

* real‑world backend structure
* AWS authentication flows
* clean separation of concerns
* production‑grade thinking without over‑engineering

It reflects how modern backend systems are built in Swiss / EU companies.

---
