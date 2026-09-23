# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Job Dossier (internal project name during development: "Application Pipeline" — still used in some file/directory names, code identifiers, and historical PLAN.md entries) is a CRM-style job search tracker. It is a portfolio project built backend-first, with AWS deployment and AI integration planned across 30 build days (see `PLAN.md`). The backend is a FastAPI modular monolith; the frontend (Next.js) and infrastructure (Terraform) have not yet been built.

## Local Development

All backend work runs from the `backend/` directory.

```bash
# Start Postgres
cd backend && docker compose up -d

# Install dependencies (uses Poetry)
cd backend && poetry install

# Run the API (from backend/)
uvicorn app.main:app --reload

# Run migrations (from backend/)
alembic upgrade head

# Generate a new migration (from backend/)
alembic revision --autogenerate -m "description"

# Lint and format
ruff check backend/ --fix
ruff format backend/

# Run tests
cd backend && pytest
```

Pre-commit hooks run `ruff` (lint + format) on `backend/` on every commit.

## Required Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in:

```
APP_ENV=dev
DATABASE_URL=postgresql+psycopg://app_pipeline_user:app_pipeline_password@localhost:5432/app_pipeline_db
COGNITO_REGION=
COGNITO_USER_POOL_ID=
COGNITO_APP_CLIENT_ID=
LLM_ENABLED=true
LLM_PROVIDER=gemini
LLM_MODEL=
GEMINI_API_KEY=
ANTHROPIC_API_KEY=
```

## Architecture

### Layer Responsibilities

The codebase uses a strict 4-layer separation. Each layer imports only downward:

```
api/routes/     → parse HTTP, call service, map domain errors to HTTP status codes
services/       → business logic + transaction boundaries (db.commit / db.refresh here only)
db/repositories/ → all ORM field mutations and queries (no commits)
domain/         → pure Python enums, ALLOWED_TRANSITIONS dict, custom exception classes
                  (zero SQLAlchemy or Pydantic imports)
```

Routes return ORM objects typed honestly (`-> Application`), FastAPI serializes them via `response_model=ApplicationRead`. Never import ORM models into routes except for type annotations.

### Key Design Decisions

- **Two-layer model approach**: `db/models/` (SQLAlchemy ORM) + `api/schemas/` (Pydantic), no intermediate domain dataclasses. `ApplicationRead` uses `ConfigDict(from_attributes=True)` so FastAPI serializes ORM objects directly.
- **State machine**: `ALLOWED_TRANSITIONS` in `domain/enums.py` defines valid stage changes. Invalid transitions raise `InvalidTransition` → mapped to `409 Conflict` in the route.
- **Auth**: `get_current_user_id()` in `api/deps.py` is currently a stub returning a hardcoded UUID. Cognito JWT verification is implemented in `core/security/cognito_jwt.py` but not yet wired into the dependency. The JWKS cache (`JWKSCache`) has 30-minute TTL and handles key rotation.
- **Partial updates**: `ApplicationUpdate` uses `model_dump(exclude_unset=True)` so PUT/PATCH only modify provided fields.

### Domain Errors → HTTP Status Codes

| Domain exception | HTTP status |
|-----------------|-------------|
| `NotFound`      | 404         |
| `Forbidden`     | 403         |
| `InvalidTransition` | 409    |
| `InvalidStageDate` | 422    |
| `CompanyHasApplications` | 409 |
| `JDNotParsed`   | 409         |
| `JDParseError`  | 502         |
| `MatchingError` | 502         |
| `FollowUpGenerationError` | 502 |

Catch and re-raise as `HTTPException` in the route layer — never let domain errors propagate to FastAPI's default handler. `backend/app/main.py` also registers global handlers for `DomainError` and bare `Exception` as a defense-in-depth fallback (mapping the same table above, defaulting to 500 for anything unmapped) — this only fires if a route forgets its own explicit mapping; it is not a substitute for the route-layer rule above. The `Exception` handler also ensures no unexpected error ever leaks internal details (stack traces, exception text) to the client — it logs server-side and returns a generic `{"detail": "Internal server error"}`.

### Alembic Notes

`alembic/env.py` imports all models via `app.db.models` (needed for autogenerate). Any new model must be imported in `backend/app/db/models/__init__.py` for Alembic to detect it.

## Coding Conventions

### Python

- Always use keyword-only arguments (`*`) in service and repository method signatures. This prevents silent positional-argument mistakes as signatures grow and makes call sites self-documenting.
- Never use `datetime.utcnow()` (deprecated, returns a naive datetime). Always use `utcnow()` from `app.db.mixins`.
- Use `from __future__ import annotations` in domain files to avoid forward-reference issues with type hints.

### SQLAlchemy

- Two separate UUID imports are required and must not be confused:
  - `from uuid import UUID as PyUUID` — used in `Mapped[PyUUID]` type hints
  - `from sqlalchemy.dialects.postgresql import UUID` — used in `mapped_column(UUID(as_uuid=True), ...)`
- Always use `DateTime(timezone=True)` on column definitions. Naive datetime columns cause subtle comparison bugs with `utcnow()`.
- Use `db.flush()` (not `db.commit()`) within a transaction when you need auto-assigned values (e.g., `id`, `created_at`) available before the transaction closes. Only services call `db.commit()` and `db.refresh()` — never repositories.
- Use `Mapped` + `mapped_column` style for all new columns. Do not use the legacy `Column(...)` style.

### Pydantic Schemas

- Every `*Read` schema must include `model_config = ConfigDict(from_attributes=True)`. Without it FastAPI cannot serialize ORM objects via `response_model`.
- Update schemas must always call `model_dump(exclude_unset=True)`. Using `model_dump()` would overwrite every field with `None` for fields the client did not send.
- `*Create` and `*Update` schemas live in `api/schemas/`; they are the API contract and may not be imported by services or repositories.

### FastAPI Routes

- Route functions return the ORM object with an honest type annotation (`-> Application`). FastAPI serializes it through `response_model`. Both annotations are always required.
- Use `def` (sync) for routes that only touch the database. Use `async def` only when the route calls an `async` dependency (e.g., Cognito JWT verification). Do not mix arbitrarily.
- Map domain exceptions to `HTTPException` in the route layer. Never let `NotFound`, `InvalidTransition`, or other domain errors reach FastAPI's default exception handler.

### Auth

- `get_current_user_id()` in `api/deps.py` is a stub returning a hardcoded UUID. It must not be used in production routes. Wire new protected routes to `require_id_token_payload` from `core/security/deps.py` and derive `user_id` from the verified token.
- Never trust user-supplied `user_id` values from request bodies. Always take `user_id` from the verified JWT via the dependency.

## Frontend (Planned — Next.js + TypeScript)

- Store tokens in memory, never in `localStorage` (exposed to XSS).
- Enable TypeScript strict mode. Do not use `any`.
- All API calls go through a single `lib/api.ts` client that attaches the `Authorization: Bearer` header. Route components do not call `fetch` directly.
