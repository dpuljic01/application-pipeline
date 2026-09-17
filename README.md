# Job Dossier

**Job Dossier** is a lightweight, CRM‑style web application that turns a chaotic job search into a **clear, measurable pipeline**.

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

**Job Dossier** fixes this by treating a job search like a real sales pipeline.

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

See **`docs/application-pipeline-summary.md`** for detailed architectural notes.

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
infra/           # Terraform / IaC (VPC, RDS, ECR, ECS Fargate, ALB, Secrets Manager)
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

### Frontend

* Next.js
* TypeScript
* shadcn/ui

### Infrastructure

* Terraform
* VPC (public/private subnets, NAT), Security Groups
* AWS ECS (Fargate), ECR
* RDS PostgreSQL, Secrets Manager
* Application Load Balancer
* S3 *(planned)*

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

### Frontend

```bash
cd frontend
cp .env.example .env.local
# fill in NEXT_PUBLIC_API_BASE_URL (http://localhost:8000/api for local backend),
# NEXT_PUBLIC_COGNITO_REGION, NEXT_PUBLIC_COGNITO_APP_CLIENT_ID

npm install
npm run dev
```

Runs at `http://localhost:3000`. Requires the backend running locally (see above) and a real Cognito user pool — there's no mock auth path.

### Infrastructure (AWS, optional)

```bash
cd infra
terraform init
terraform plan -var="image_tag=$(git rev-parse --short HEAD)"
terraform apply "tfplan"
```

Requires an AWS profile with the right permissions configured (see `provider "aws"` in `main.tf`) and a Docker image already built/pushed to ECR for that tag (`docker build --platform linux/amd64 ...`, then `docker push`). This stack costs real money while running — the NAT Gateway alone is ~$0.045/hr — so the intended workflow is `apply` before a demo, `terraform destroy` right after, not leaving it up. See `docs/application-pipeline-summary.md` §20-26 for the concepts and gotchas behind each piece.

---

## Design Principles

* Explicit > implicit
* Boring tech > clever abstractions
* Business logic isolated from frameworks
* Every layer has one responsibility

If a piece of code is hard to explain, it’s probably in the wrong layer.

---

## Documentation

* `docs/application-pipeline-summary.md` – core concepts & mental models
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
