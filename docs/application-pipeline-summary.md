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
