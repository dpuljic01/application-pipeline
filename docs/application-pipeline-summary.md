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
* `core/` – shared utilities, config
* `integrations/` *(planned, Day 14+)* – AWS / external services (LLM providers, SES, S3)

---

## 2. Layer Responsibilities (Very Important)

### API Layer (`api/`)

**What it does:**

* Receives HTTP requests
* Validates input (Pydantic)
* Calls services
* Returns HTTP responses

* Catches domain exceptions and maps them to HTTP status codes — `NotFound` → 404, `InvalidTransition` → 409 (a conflict with existing state, not a malformed request, so not 400)

**What it must NOT do:**

* No business logic
* No database queries
* No AWS SDK calls

Think: *"Translate HTTP → Python — including turning domain failures into deliberate, typed responses."*

---

### Service Layer (`services/`)

**What it does:**

* Business rules
* Orchestration
* Coordinates repositories + integrations
* Owns the transaction boundary — the only layer that calls `db.commit()` / `db.refresh()`

**Examples:**

* Create application
* Change status
* Send notification

**What it must NOT do:**

* No HTTP knowledge
* No SQLAlchemy session handling
* No relying on a repository to commit for it

Think: *"This is the brain — and the only place a transaction ends."*

---

### Domain Layer (`domain/`)

**What it does:**

* Pure business concepts
* Enums, value objects, rules
* Explicit state machine: `ALLOWED_TRANSITIONS` — a `dict[ApplicationStage, set[ApplicationStage]]` defining which stage changes are legal
* Custom exception classes for business-rule violations (`NotFound`, `InvalidTransition`)

**Examples:**

* `ApplicationStatus` — `SAVED → APPLIED → INTERVIEW → OFFER → ACCEPTED`, plus terminal states (`REJECTED`, `WITHDRAWN`, `GHOSTED`)
* `SAVED` can only transition to `APPLIED` or `WITHDRAWN` — going straight to `INTERVIEW` is invalid and raises `InvalidTransition`

**Rules:**

* No FastAPI
* No SQLAlchemy
* No AWS
* Testable as pure functions — no DB, no HTTP, just Python

Think: *"Business truth, framework-free — including what counts as a violation."*

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

## 12. JWT, JWKS, and JOSE (Deep Dive – Day 4)

### JOSE Standards (Foundation)

**JOSE** = *JavaScript Object Signing and Encryption*  
A family of standards that define how tokens are signed, verified, and represented.

Relevant parts:

- **JWT (JSON Web Token)** – token format (`header.payload.signature`)
- **JWS (JSON Web Signature)** – how JWTs are signed (e.g. RS256)
- **JWK (JSON Web Key)** – JSON representation of a cryptographic key
- **JWKS (JSON Web Key Set)** – a set of public keys published by the issuer

**Key idea:**  
JWTs are verified using public keys defined by JOSE standards, not custom cryptography.

---

### Why JWKS Exists

**Problem JWKS solves:**

- Cognito signs tokens with **private keys**
- Backend must verify tokens **without knowing private keys**
- Keys must be **rotatable** without breaking clients

**Solution:**

- Cognito publishes **public keys** at a well-known JWKS endpoint
- JWT header contains `kid` (key ID)
- Backend selects the correct public key by `kid`

**Result:**

- No shared secrets
- Stateless authentication
- Safe key rotation

---

### JWKS Fetch + Cache Pattern (Critical)

**Why caching is mandatory:**

- Fetching JWKS on every request is slow and unnecessary
- Keys change rarely
- JWKS is public but still a network dependency

**Correct strategy:**

1. Fetch JWKS once
2. Cache in memory with TTL
3. Reuse for all requests
4. Refresh only when:
   - TTL expires, or
   - token `kid` is not found (key rotation case)

**Important mistake avoided:**

- Never clear cache on every request
- Refresh **only** on cache expiry or key-miss

---

### JWT Verification (Backend Responsibility)

**Backend verification steps (non-negotiable):**

1. Extract token from `Authorization: Bearer <JWT>`
2. Read JWT header **without trusting payload**
3. Select JWK by `kid`
4. Verify cryptographic signature (RS256)
5. Validate standard claims:
   - `iss` – issuer (Cognito user pool)
   - `aud` – audience (app client id)
   - `exp` – expiration
6. Extract trusted claims (`sub`, `email`, etc.)

**Important principle:**

> Decoding ≠ verification  
> Verification must always include signature + claims.

---

### `iss` and `aud` (Why They Are Not in Models)

- `iss` and `aud` are **security constraints**
- They are validated at the boundary
- They are **not application data**

**Design rule:**

- Validate → discard
- Do not pass `iss` / `aud` into business logic
- Keep them out of response models

This prevents coupling API contracts to auth internals.

---

### `at_hash` and ID Tokens (Important Edge Case)

**What happened:**

- Cognito ID tokens may contain `at_hash`
- `python-jose` tries to validate it
- Backend only receives one token (ID token)
- Access token is not available → verification fails

**Correct resolution:**

- Disable `at_hash` verification on backend
- Rely on:
  - signature
  - `iss`
  - `aud`
  - `exp`

**Why this is correct:**

- `at_hash` is mainly for frontend / OIDC clients
- Backends typically validate tokens independently

---

## 13. ID Token vs Access Token (Very Important)

### ID Token

**Purpose:**

- Identity
- Who the user is

**Contains:**

- `sub`
- `email`
- profile data

**Used for:**

- `/me`
- user bootstrap
- identity mapping

---

### Access Token

**Purpose:**

- Authorization
- What the user is allowed to do

**Used for:**

- Protecting API endpoints
- Scopes / groups / permissions

---

### Rule

- `/me` → **ID token**
- Business APIs → **access token**

Do not mix them.

---

## 14. `/me` Endpoint – Correct Semantics

**What `/me` represents:**

> “Who is the currently authenticated user?”

**Responsibilities:**

- Verify authentication end-to-end
- Prove JWT verification works
- Return identity data only

**What `/me` should return:**

- `sub` (stable user identifier)
- Optional identity fields (`email`, `username`)

**What `/me` should NOT return:**

- `token_use`
- `iss`, `aud`
- scopes, groups, or permissions
- raw tokens

**Reason:**

- `/me` is an identity endpoint, not an auth-debug endpoint
- Authentication mechanics stay server-side

---

## 15. OAuth2 Flow vs Backend Responsibilities

**OAuth2 Authorization Code Flow:**

1. Browser → Cognito `/oauth2/authorize`
2. Cognito → Browser with `code`
3. Client exchanges `code` → `/oauth2/token`
4. Cognito returns:
   - `id_token`
   - `access_token`
5. Client sends JWT to backend

**Backend never sees:**

- username / password
- authorization `code`
- refresh token

**Backend only cares about:**

- JWT verification
- claim validation
- identity extraction

---

## 16. Authentication Testing Strategy (Day 4)

**Tests performed:**

- Valid token → 200
- Missing token → 401/403
- Tampered token → 401
- Wrong issuer → 401
- Wrong audience → 401
- Expired token → 401
- JWKS fetched once and cached correctly

**Outcome:**

Authentication pipeline is correct, secure, and production-aligned.

---

## 17. Key Takeaways

- Authentication is a **boundary concern**
- JWTs must always be **verified**, never trusted
- JWKS enables **stateless, scalable auth**
- Cache correctness matters as much as cryptography
- Identity and authorization are **separate concerns**
- Clean boundaries beat clever abstractions

---

## 18. Transaction Boundaries: Why Stage Changes Write History Atomically (Day 3 addendum)

**The gap:** `PATCH /applications/{id}/stage` validated the transition and updated `stage`/`stage_changed_at`, but never wrote an `Activity` record. History (`ActivityService.log_activity`) was a fully separate, manually-triggered path — so an automated stage change and the audit trail could silently drift apart.

**The decision:** `ApplicationService.change_stage()` now does both writes — `ApplicationRepository.update_stage()` and `ActivityRepository.create(activity_type=STAGE_CHANGE, ...)` — through the **same session**, inside the **same `db.commit()`**.

```python
self.repository.update_stage(application=app, stage=stage)
activity = self.activity_repository.create(
    application_id=app.id,
    activity_type=ActivityType.STAGE_CHANGE,
    note=f"{from_stage.value} -> {stage.value}",
)
self.db.flush()
app.last_activity_at = activity.created_at

self.db.commit()   # single commit — both writes succeed or neither does
self.db.refresh(app)
```

**Why this matters (the rule, not just this case):**

- Two related writes that must both happen or neither happen belong in **one transaction**, not two service calls each with their own commit.
- This is exactly why `CLAUDE.md` restricts `db.commit()`/`db.refresh()` to the **service layer only** — repositories never commit, so services stay free to compose multiple repository calls into one atomic unit of work.
- The alternative (calling `ActivityService.log_activity()` separately, with its own commit) would create a window where a stage change could succeed and the history write could fail independently — silent data drift, hard to debug later.

**Interview framing:** *"What happens if the second write fails?"* — with one shared session and one commit, it doesn't matter: nothing is persisted until both writes are staged, so a failure mid-way rolls back the whole operation. That's the same reasoning behind `db.flush()` before `db.commit()` here — flush assigns `activity.created_at` (a Python-side default) without ending the transaction, so `last_activity_at` can be set from a value that's guaranteed consistent with what's about to be committed.

---

## 19. Testing Strategy: Transactional Rollback per Test (Day 5)

**Decision:** Tests don't get a dedicated test database or `drop_all`/`create_all` between runs. Each test opens one DB connection, starts an outer transaction, and runs inside a SAVEPOINT that's automatically restarted every time application code calls `db.commit()`. At teardown, the **outer transaction is rolled back**, so nothing a test does is ever actually persisted — regardless of how many `commit()` calls happened inside it.

**Why not just point tests at a throwaway database?** Would work too, but this pattern:

- Makes every test isolated **and free of setup/teardown cost** (no schema recreation, no per-test data wipe) — the full 22-test suite runs in ~0.2s.
- Lets service-layer code call `db.commit()` exactly as it does in production, so the tests exercise the real transaction boundaries instead of a mocked-out session.
- Works identically against local dev data — tests can run against the same Postgres a developer is using interactively without any risk of leaving rows behind.

**The FastAPI wiring:** the `client` fixture overrides both `get_db` (yields the test's transactional session, not a fresh one per request) and `get_current_user_id` (returns a fixture-created user), via `app.dependency_overrides`. That's the same DI seam described in §3 — tests replace the *outer* dependency, not the service/repository code underneath it.

**Gotcha hit while wiring this up:** `docker compose up -d` can silently not be "the database" if another Postgres is already bound to `localhost:5432` (a native Homebrew service, in this case) — the app connects fine either way if credentials happen to match, so nothing errors, it's just quietly running against the wrong Postgres. Worth checking `lsof -iTCP:5432 -sTCP:LISTEN` if DB behavior ever looks inconsistent with what `docker-compose.yml` describes.
