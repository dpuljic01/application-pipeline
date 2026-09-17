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

**Live (free tier, always on):**
* [Render](https://render.com) — backend, Docker runtime, deployed from `render.yaml`
* [Neon](https://neon.tech) — external Postgres (Render's own free Postgres expires after 30 days, so the database lives outside Render)
* [Vercel](https://vercel.com) — frontend
* Custom domains on `puljic.ch`: `api.puljic.ch` (backend) and `jobs.puljic.ch` (frontend)

**Optional (AWS, spun up on demand for interviews/demos, not run 24/7):**
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

### Live Deployment (Render + Neon + Vercel, free tier)

This is the actual always-on deployment — simpler than the AWS path below, and free.

**Backend (Render):**
1. Connect this repo in the Render dashboard via "New > Blueprint" — it reads `render.yaml` automatically (Docker runtime, free plan, health check at `/api/health`).
2. Create a [Neon](https://neon.tech) Postgres project and paste its connection string into Render's `DATABASE_URL` env var (`sync: false` in `render.yaml` — set manually, not committed).
3. Set the other `sync: false` env vars in the Render dashboard: `CORS_ORIGINS` (the Vercel frontend's origin), `GEMINI_API_KEY`/`ANTHROPIC_API_KEY`, `ADZUNA_APP_ID`/`ADZUNA_APP_KEY`.
4. Custom domain: add `api.puljic.ch` under the Render service's Settings → Custom Domains, then add a CNAME record for `api` in your DNS provider pointing at the target Render gives you. Render auto-issues a Let's Encrypt cert once DNS resolves — usually a few minutes.
5. **Run migrations against Neon after every deploy that adds one** — Render does not do this automatically: `DATABASE_URL="<neon connection string>" poetry run alembic upgrade head` from `backend/`, or via Neon's own SQL editor. Skipping this is a real, repeatable failure mode: it 500s `GET /applications` (and anything else touching the changed table) until the migration runs, and it's bitten this project twice already (Day 9's `parsed_jd` column, Day 10's `match_score`/`match_details`).

**Frontend (Vercel):**
1. Import this repo as a Vercel project (root: `frontend/`).
2. Set `NEXT_PUBLIC_API_BASE_URL=https://api.puljic.ch/api` and `NEXT_PUBLIC_COGNITO_REGION`/`NEXT_PUBLIC_COGNITO_APP_CLIENT_ID` as **Config** (not Secret) environment variables — this app is 100% client-rendered, so the browser itself needs to read these at runtime; a Secret-type variable is write-only and can't be read back client-side.
3. Custom domain: add `jobs.puljic.ch` under the Vercel project's domain settings, same CNAME-then-wait-for-cert pattern as Render.

### Infrastructure (AWS, optional)

```bash
cd infra
terraform init
terraform plan -var="image_tag=$(git rev-parse --short HEAD)"
terraform apply "tfplan"
```

Requires an AWS profile with the right permissions configured (see `provider "aws"` in `main.tf`) and a Docker image already built/pushed to ECR for that tag (`docker build --platform linux/amd64 ...`, then `docker push`). This stack costs real money while running — the NAT Gateway alone is ~$0.045/hr — so the intended workflow is `apply` before a demo, `terraform destroy` right after, not leaving it up. Not the live deployment path (see above) — kept as a from-scratch AWS reference and for demos where that specifically matters. See `docs/application-pipeline-summary.md` §20-26 for the concepts and gotchas behind each piece.

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
