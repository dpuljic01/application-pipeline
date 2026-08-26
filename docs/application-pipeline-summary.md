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

---

## 20. VPC Network Layer: Why the Database Goes in a Private Subnet (Day 13)

**The distinction is pure routing, not a subnet property.** A subnet is only "public" because its route table sends `0.0.0.0/0` to an Internet Gateway; "private" just means that route is missing (or points at a NAT Gateway instead). Nothing about a subnet's own definition marks it public or private — `vpc.tf` builds both from the same `aws_subnet` resource, differing only in which route table gets associated with them.

**Why RDS and ECS tasks sit in private subnets:** no route to an Internet Gateway means no inbound path from the internet exists at all, regardless of security group rules — it's not "blocked," it's "unreachable." Security groups are a second, independent layer on top of that: `aws_security_group.rds` only allows inbound 5432 from `aws_security_group.ecs`, so even something else inside the same VPC can't reach Postgres unless it's specifically the app tier. Two layers, two different failure modes closed: routing closes "reachable from outside the VPC at all," security groups close "reachable from other things inside the VPC."

**Why private subnets still need a NAT Gateway:** RDS and ECS tasks have no inbound path, but they still need *outbound* internet access — ECS has to pull images from ECR, the app may need to call external APIs. A NAT Gateway (`aws_nat_gateway.main`, sitting in a *public* subnet) provides exactly that: outbound-only, translated through a single public IP, no inbound connections can be initiated from the internet through it. This is also the most expensive piece of the whole stack (~$0.045/hr flat, regardless of traffic) — see §26.

**Interview framing:** *"Why not just rely on the security group and skip the private subnet?"* — because a security group is a rule you could misconfigure or a future engineer could loosen; a private subnet with no IGW route is a structural guarantee that doesn't depend on anyone getting a rule right. Defense in depth: security groups can fail open through human error, routing can't.

---

## 21. `awsvpc` Networking Mode and ENIs (Day 14)

**The concept:** an ENI (Elastic Network Interface) is AWS's term for a virtual network card — its own private IP, its own MAC address, its own attached security groups, plugged into a specific subnet.

**Why it matters for Fargate:** ECS's older networking mode (`bridge`) has containers share their host EC2 instance's single network interface, NAT'd through it — the container has no real address of its own on the VPC. `network_mode = "awsvpc"` (mandatory for Fargate) instead gives **each task its own ENI**, with a genuine private IP inside `aws_subnet.private`. That's the concrete reason `aws_security_group.ecs` in `vpc.tf` attaches directly to the task, and why the ALB target group has to use `target_type = "ip"` rather than `"instance"` — there's no EC2 instance ID to register, only IPs that come and go as tasks start and stop. ECS registers/deregisters each task's IP with the target group automatically via the service's `load_balancer` block; no manual attachment resource needed.

---

## 22. Secrets Manager: What It Actually Fixes, and What It Doesn't (Day 13)

**The starting problem:** `rds.tf` originally took the DB password as a plain Terraform variable (`var.db_password`), set from `terraform.tfvars`. `sensitive = true` on a variable only redacts it from CLI *output* — it does nothing to `terraform.tfstate`, which records the resolved value of every attribute in plaintext regardless.

**What moving to `random_password` + Secrets Manager actually buys:**
1. No password hand-typed into a `.tfvars` file or shell history — Terraform generates it once, internally.
2. ECS gets a clean way to pull the value at runtime via `valueFrom`, scoped by IAM, instead of the alternative — threading it through as a plain environment variable that shows up readably in the ECS console/task metadata.

**What it does *not* fix:** `random_password.db_password.result` still ends up in `terraform.tfstate`, because Terraform has to track it to detect drift on future applies. Nothing Terraform directly manages fully escapes state exposure — the real mitigation for that is securing the state file itself (encrypted remote backend, restricted access), out of scope for a local-state solo project. Worth being precise about this distinction rather than claiming "credentials are never in state," which isn't true.

**A real constraint this surfaced — composing `DATABASE_URL`:** the app expects one `DATABASE_URL` connection string (`postgresql+psycopg://user:pass@host:port/db`), not separate `DB_HOST`/`DB_PASSWORD` env vars. ECS's `secrets` block can inject an *entire* secret value as one env var, or a single JSON key from it — it cannot interpolate a secret into the middle of a larger string. So the secret has to store the fully composed URL (built in Terraform from `aws_db_instance.main.endpoint`, `.username`, `.db_name`, and `random_password.db_password.result`), not just the bare password.

**Gotcha for a destroy/recreate workflow:** Secrets Manager defaults to a **30-day recovery window** on deletion. `terraform destroy` then `apply` again later (this project's whole cost-management pattern) would fail on the second apply — a secret with that name is still "pending deletion." Fixed with `recovery_window_in_days = 0`, which forces immediate deletion. Wrong choice for anything needing real recoverability, correct here.

---

## 23. IAM: Two Different Least-Privilege Stories (Day 14)

### Task execution role vs. task role

Two different *who* and *when*: the **execution role** is assumed by ECS itself, *before* the container runs — pulling the image from ECR, fetching `DATABASE_URL` from Secrets Manager to hand to the container as an env var. The **task role** is assumed by the *application code*, *while running*, for any AWS API calls it makes itself. This app doesn't call AWS APIs yet (only Postgres, over network — a security group concern, not IAM), so the task role is empty today, existing only so Day 15's S3 access has somewhere to attach. One sentence version: *the execution role is what ECS needs to start the container; the task role is what the container needs once it's running.* Separating them limits blast radius — application code inheriting ECS's own infrastructure-level permissions (arbitrary image pulls, arbitrary secret reads) would be a much bigger surface than it needs.

### Scoping the Terraform deploy user itself

A separate, equally real lesson: `app-pipeline-terraform` (the IAM user Terraform runs as) started with only `AmazonRDSFullAccess` + `AmazonVPCFullAccess` attached — Day 14 needed ECR/ECS/ELB/Logs/Secrets Manager too, none of which it had. Extended with matching AWS-managed `*FullAccess` policies for those services — **except IAM**, which got a hand-scoped custom policy instead, restricted to `arn:aws:iam::<account>:role/app-pipeline-*`. Reasoning: a user with `IAMFullAccess` can create a *new* role or user with admin rights and grant itself anything — the classic privilege-escalation path, and exactly what turns "a leaked CI credential" into "a fully compromised account." Scoping by resource ARN means this user can manage *this project's* roles and nothing else's.

**Gotcha hit twice:** role *deletion* needs more read permissions than role *creation* does — `iam:ListInstanceProfilesForRole` and `iam:ListRoleTags` are both called by Terraform's provider as pre-delete checks, and got missed in the first pass of the scoped policy, only surfacing when `terraform destroy` actually hit them. Worth remembering: a scoped IAM policy written by only looking at `create`/`attach` calls will usually be incomplete for `delete`.

**Also easy to miss:** the policy needs `iam:PassRole`, scoped to the same role ARNs — the permission that lets Terraform *hand* those roles to ECS. `CreateRole` alone isn't enough; without `PassRole`, ECS can't actually assume the role Terraform just created for it.

**A structural note on who can grant this:** `app-pipeline-terraform` cannot read or modify its own IAM policy (`iam:ListAttachedUserPolicies` etc. aren't in its permission set) — granting it *more* access requires a separate, more privileged identity (the account's root/admin credentials here). That's deliberate: the identity a deploy pipeline runs as should never be able to escalate its own privileges.

---

## 24. ECR: Immutable Tags and the `force_delete` Trade-off (Day 14)

**`image_tag_mutability = "IMMUTABLE"`:** once a tag is pushed, it can never be overwritten — pushing `:latest` a second time fails outright. This forces every build to get a genuinely unique tag (git short SHA here), which means every deployed image is traceable to an exact commit and rollback-by-tag is reliable. The cost: a manual `docker push image:latest` workflow, common in tutorials, simply doesn't work under this setting — deliberate.

**`force_delete = true`:** by default, AWS refuses to delete an ECR repository that still contains images — `terraform destroy` fails with `RepositoryNotEmptyException` unless images are removed first. Given this project's workflow is `apply` before a demo/dev session and `destroy` right after, that default would block every single teardown. `force_delete = true` removes the guardrail — a reasonable trade here specifically because every image is trivially rebuildable from the committed Dockerfile plus a git SHA; the guardrail wasn't protecting anything real for a repo meant to be destroyed and recreated on a cycle.

---

## 25. Docker + Poetry: Two Real Gotchas, Plus a Private-Subnet Migration Pattern (Day 14)

**Gotcha 1 — non-deterministic venv path breaks multi-stage builds.** A naive multi-stage Dockerfile setup used `POETRY_VIRTUALENVS_PATH=/opt/venvs` with `virtualenvs.create=true`, then tried to `COPY --from=builder /opt/venvs/*/bin` into the runtime stage. Two problems: Poetry names that folder from a hash of the project + Python version, not something guessable, *and* `ENV` instructions in a Dockerfile aren't a shell context — the `*` glob never expands, so `PATH` ends up containing the literal string `/opt/venvs/*/bin`, which doesn't exist. Fix: `POETRY_VIRTUALENVS_IN_PROJECT=true`, which always creates the venv at a fixed `/app/.venv` — no guessing, no glob needed.

**Gotcha 2 — Poetry version must match what generated the lock file.** `pyproject.toml` here uses the PEP 621-style `[project]` table for dependencies (not the older `[tool.poetry.dependencies]` layout) — natively supported only from Poetry 2.0 onward. A Dockerfile pinning `POETRY_VERSION=1.8.3` while the local lock file was generated by Poetry 2.3.1 would either misread the dependency list or fail outright. The fix is mechanical (pin the same version), but the lesson generalizes: a Dockerfile's tool versions are a second place version drift can hide, separate from the lock file itself.

**Gotcha 3 — build platform vs. Fargate's default.** The dev machine is Apple Silicon (ARM64/`aarch64`); the ECS task definition has no `runtime_platform` block, which means Fargate defaults to **X86_64**. Building without `docker build --platform linux/amd64` produces an ARM64 image that fails on Fargate with an exec-format error — a common real-world gotcha for anyone on Apple Silicon deploying to default (non-Graviton) Fargate.

**Running migrations against a private-subnet database — no bastion needed:** RDS has no public accessibility (correctly, by design — see §20), so `alembic upgrade head` can't run from a laptop. The pattern used instead: `aws ecs run-task`, same task definition and same network placement (private subnets, `aws_security_group.ecs`) as the real service, but with the container `command` overridden to `["alembic", "upgrade", "head"]` instead of `uvicorn`. It runs once, applies the schema, exits — no bastion host, no temporarily opening RDS to the internet, no new infrastructure. Worth remembering as a direct answer to "how do you run one-off admin commands against infrastructure that has no public entry point."

---

## 26. Cost Management for a Solo/Demo AWS Project

**The real cost drivers, in order:** the NAT Gateway is the single biggest line item (~$0.045/hr flat, ~$32-35/mo if left running continuously, charged whether or not it's used) — everything else in this stack (RDS `db.t4g.micro`, ALB, Fargate at 256/512, one Secrets Manager secret) is close to free at this scale, especially within the free tier's first 12 months.

**The workflow this drives:** treat the stack as demo-on-demand — `terraform apply` before a review/interview/demo, `terraform destroy` right after — rather than leaving it running 24/7. This is also a legitimate interview answer about cost discipline, not just a hack to save money personally.

**A billing-console gotcha worth knowing:** the NAT Gateway (and its Elastic IP, and general data transfer) bills under **"EC2-Other,"** not under any VPC or NAT-specific line item — despite this project having zero actual EC2 *instances*. "EC2 shows up in the bill" does not mean "an EC2 instance exists somewhere"; Fargate is genuinely serverless, and Cost Explorer's category names don't map cleanly onto what you actually provisioned.

**A second layer of protection:** an AWS Budget alert (separate from Cost Explorer, which lags ~24h) checks spend roughly daily and can email at custom thresholds — a backstop for "forgot to destroy this" that doesn't depend on remembering to go check a dashboard.
