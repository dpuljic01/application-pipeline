# Application Pipeline – Core Concepts

Quick-reference notes summarizing the **key backend, AWS, and architecture concepts** used so far. This is meant to be skimmed when in doubt.

---

## 1. Architecture Overview

**Goal:** Interview-ready, scalable, but simple architecture.

**Pattern:** Modular monolith (not microservices).

**Why:**

* Faster development
* Easier testing
* Clear separation of concerns
* Can evolve into microservices later

**High-level layers:**

* `api/` – HTTP layer (FastAPI routers)
* `services/` – business logic
* `domain/` – core models + rules
* `db/` – persistence (SQLAlchemy)
* `integrations/` – AWS / external services
* `core/` – shared utilities, config

---

## 2. Layer Responsibilities (Very Important)

### API Layer (`api/`)

**What it does:**

* Receives HTTP requests
* Validates input (Pydantic)
* Calls services
* Returns HTTP responses

**What it must NOT do:**

* No business logic
* No database queries
* No AWS SDK calls

Think: *"Translate HTTP → Python"*

---

### Service Layer (`services/`)

**What it does:**

* Business rules
* Orchestration
* Coordinates repositories + integrations

**Examples:**

* Create application
* Change status
* Send notification

**What it must NOT do:**

* No HTTP knowledge
* No SQLAlchemy session handling

Think: *"This is the brain"*

---

### Domain Layer (`domain/`)

**What it does:**

* Pure business concepts
* Enums, value objects, rules

**Examples:**

* `ApplicationStatus`
* Validation rules

**Rules:**

* No FastAPI
* No SQLAlchemy
* No AWS

Think: *"Business truth, framework-free"*

---

### DB Layer (`db/`)

**What it does:**

* SQLAlchemy models
* Repositories
* Database access

**Repository pattern:**

* `ApplicationRepository`
* `UserRepository`

**Why repositories:**

* Decouple business logic from DB
* Easier testing

---

## 3. Dependency Injection (DI)

**What DI is:**
Passing dependencies instead of creating them inside functions.

**Why:**

* Testability
* Loose coupling
* Cleaner code

**FastAPI DI example:**

* `Depends(get_db)`
* `Depends(get_current_user)`

**Rule:**

* API injects dependencies
* Services receive them as arguments

---

## 4. UUID vs Integer IDs

**Why UUIDs:**

* Safe for public APIs
* No ID guessing
* Distributed-system friendly

**Where used:**

* User IDs
* Application IDs

**Rule:**

* UUID exposed externally
* Internal DB can still optimize with indexes

---

## 5. Authentication with AWS Cognito

### Cognito Basics

* **User Pool** = user database
* **App Client** = application using the pool
* **Hosted UI** = login/register UI

**Flow used:**

* OAuth2 Authorization Code Flow

---

### Tokens

Cognito issues **JWTs**:

* ID Token – user identity
* Access Token – API authorization

**Important:**

* Backend never trusts frontend
* Backend verifies JWTs

---

### JWT Verification

**Steps:**

1. Extract token from `Authorization: Bearer ...`
2. Fetch JWKS (public keys)
3. Verify signature
4. Validate claims (issuer, audience)
5. Extract `sub`

`sub` = Cognito user ID (immutable)

---

## 6. `/me` Endpoint Pattern

**Purpose:**

* Verify authentication
* Map Cognito user → internal user

**Flow:**

* Frontend sends access token
* Backend verifies token
* Backend finds or creates user
* Returns internal user profile

This endpoint proves the auth pipeline works.

---

## 7. Frontend Auth (Minimal)

**Frontend responsibilities:**

* Redirect to Cognito Hosted UI
* Handle callback
* Store token (memory or secure storage)
* Send token to backend

**Frontend must NOT:**

* Decode tokens for authorization logic

---

## 8. Environment Configuration

**Rule:**

* No secrets in code
* Everything via environment variables

**Examples:**

* `COGNITO_USER_POOL_ID`
* `COGNITO_CLIENT_ID`
* `DATABASE_URL`

---

## 9. AWS Choices (Intentional)

### ECS + Fargate

* No server management
* Pay per usage
* Perfect for demo + production

### RDS Postgres

* Real production DB
* Matches Swiss enterprise expectations

### S3

* File storage

### EventBridge

* Scheduled jobs (later reminders)

---

## 10. Design Philosophy (Interview-Critical)

* Simple first, extensible later
* Clear boundaries > clever abstractions
* Explicit over implicit
* Boring tech wins

If you can **explain why each layer exists**, you are already above average.

---

## 11. Mental Checklist When Coding

Before writing code, ask:

* Which layer does this belong to?
* Does this layer know too much?
* Can I test this without FastAPI/AWS?

If yes → good design.

---

End of cheat sheet.
