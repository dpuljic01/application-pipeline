# Application Pipeline — Compressed Build Plan

> ~18 working days · 2–3 hours each · Backend-first, AWS deploy, AI integration
>
> This is a compressed version of the original 30-day plan, cut down for a tighter
> timeline while keeping the two biggest interview differentiators intact: the
> AI integration phase and a real AWS deployment. See "What Was Cut" below for
> the full list of what got dropped and why — those items double as good answers
> to "what would you add next?" in an interview.

---

## How to Use This Document

Each day is a self-contained story. Every story follows this structure:

- **Goal** — what you're building and why it matters
- **Context** — how it connects to real-world systems and interviews
- **Tasks** — concrete steps, ordered
- **Acceptance Criteria** — how you know it's done
- **Stretch** — optional if you have extra time
- **Learning Checkpoint** — question to verify you understood the concept, not just copied code

Work linearly. Each day builds on the previous one. If a day takes longer than 3 hours, stop at a clean commit point and finish it the next session.

---

## Current Status

- ✅ Day 1 — Docker + Postgres + Alembic
- ✅ Day 2 — Application Model + CRUD
- ✅ Day 3 — Application Status Machine
- ✅ Day 5 — Testing Foundation (pytest + CI landed early); filtering/sorting/pagination still open
- ✅ Day 6 — Cognito Setup + JWT Verification (JWKS cache, `/me` endpoint, `core/security/`)
- ⬜ Day 4 — Company Model + Relationships (next up)
- 🟨 Day 7 — Route protection done (`get_current_user_id()` stub replaced with real `get_current_user`, verified against live Cognito); still open: global exception handler with consistent JSON error shape, JWKS-unreachable → 503
- 🟨 Day 17 — pulled forward, out of order (see `frontend/`): login + application dashboard (table, add-application dialog, stage-change dropdown honoring `ALLOWED_TRANSITIONS`) built and verified against live Cognito + the real API. Deviates from the plan on two points: direct login form calling Cognito's `InitiateAuth` instead of the documented Hosted UI redirect, and no token persistence across page refresh (in-memory only, by design, no silent refresh yet). Match score and everything else in Day 17/18 still blocked on Days 8-16.
- ⬜ Deploy (compresses Days 13-14, not started) — decided 2026-08-17: backend to AWS via Terraform (VPC, RDS, ECR, ECS Fargate, ALB with HTTPS/ACM — PLAN.md's plain-HTTP ALB isn't enough once the frontend is on Vercel, since browsers block HTTPS→HTTP calls), frontend to **Vercel** rather than AWS (never an actual AWS-learning goal in this plan, and the app is 100% client-rendered already so it doesn't need a Next.js server). Domain: `api.puljic.ch` (hosttech DNS, same domain as the portfolio site). Out of scope for the first pass: GitHub Actions → ECS (Day 16), S3 docs (Day 15), Route53, Multi-AZ/autoscaling. **Important:** user wants to write the Terraform themselves with step-by-step guidance, not receive finished `.tf` files — see `feedback-teach-aws-topics` memory.

---

## What Was Cut (and why)

Compared to the original 30-day plan, this version drops or trims:

- **Background task queue + reminder rules engine** (was Days 11–13: Redis/`arq`, `ReminderRule`, hourly polling task). Cut almost entirely — it's real infra experience, but it's not what makes this app *feel* working, and it's the least interview-differentiating piece relative to its build cost.
- **SES email sending** (was Day 13). Was only wired to send reminder emails — with reminders cut, its trigger is gone. The follow-up email generator still produces email drafts (Day 11), just doesn't send them.
- **EventBridge scheduled tasks** (was Day 24). No longer needed without reminders/digests to schedule.
- **Full monitoring/alarms buildout** (was Day 26: Prometheus-style `/metrics`, 5 CloudWatch alarms, dashboard). Trimmed to structured logging only, folded into the CI/CD day as a light add-on.
- **Auth hardening depth** (was Day 10: rate limiting, `structlog` request-id correlation, full error-response schema). Trimmed to the essentials — global exception mapping stays, `slowapi` rate limiting and structured logging become stretch goals.
- **Local file storage** (was Day 6: upload to `./uploads/`, then migrate to S3 later). Skipped the local-only step — document storage goes straight to S3 when it's built (Day 15), since building local storage just to replace it wastes a day without adding interview signal.
- **LLM provider benchmarking CLI + `llm_benchmarks` table** (part of original Day 19). Trimmed to basic cost tracking + output validation + caching; the formal benchmark tooling becomes a stretch goal.

If an interviewer asks "what's next" or "what would you build with more time," this list is a ready-made answer — it shows you scoped deliberately under a deadline, not that you didn't know these things existed.

---

## Phase 1: Core Backend Foundation (Days 1–5)

### Day 1 — Docker + PostgreSQL + Alembic Baseline ✅

**Goal:** Reproducible local dev environment with a real migration workflow.

**Context:** Every production backend needs deterministic database migrations. `docker compose up` should give any developer a working system in under 60 seconds. This is table stakes in Swiss companies — interviewers will check.

**Tasks:**
1. `docker-compose.yml` with `postgres:16` and the FastAPI app service.
2. `alembic` configured with the async SQLAlchemy engine, reading `DATABASE_URL` from env vars.
3. Initial migration (empty — just proves the pipeline works).
4. `GET /health` returns `{"status": "ok", "db": true}` (actually pings Postgres).

**Acceptance Criteria:**
- `docker compose up -d` starts Postgres, API responds on `localhost:8000`.
- `alembic upgrade head` runs cleanly.
- `GET /health` returns 200 with DB confirmation.

**Learning Checkpoint:** What's the difference between `alembic upgrade head` and `alembic stamp head`? When would you use each?

---

### Day 2 — Application Model + CRUD Endpoints ✅

**Goal:** Core `Application` model with full CRUD through the API layer.

**Context:** This is the central entity. Get the layering right here and everything else follows.

**Architecture Decision — 2-layer model approach (no `domain/models.py`):**

```
db/models/          → SQLAlchemy ORM models (source of truth for DB shape)
api/schemas/        → Pydantic schemas for request/response (ApplicationCreate, ApplicationRead, ApplicationUpdate)
domain/             → Pure Python only: enums, error classes, business rules (no SQLAlchemy, no Pydantic)
```

Never expose ORM models directly in the API. `ApplicationRead` uses `model_config = ConfigDict(from_attributes=True)` so FastAPI can serialize ORM objects via `response_model` without manual mapping.

**Layer responsibilities:**
- **Route**: parse HTTP input, call service, catch domain errors and map to HTTP status codes, return ORM object
- **Service**: owns business logic and transaction boundaries (`db.commit()` / `db.refresh()` live here)
- **Repository**: owns all data access and ORM field mutations — service never sets ORM attributes directly
- **Domain**: pure Python enums, `ALLOWED_TRANSITIONS` dict, custom exception classes

**Acceptance Criteria:**
- All 5 endpoints (`POST`, `GET` list, `GET` by id, `PUT`, `PATCH .../stage`) work via curl/httpie.
- Missing required fields returns 422; non-existent UUID returns 404.
- `domain/` has zero SQLAlchemy or Pydantic imports.
- Routes never import from `db/models/` except for type annotations.

**Learning Checkpoint:** Why use two layers (ORM + Pydantic) instead of three (domain dataclass + ORM + Pydantic)? When does the third layer pay off?

---

### Day 3 — Application Status Machine ✅

**Goal:** Enforce valid status transitions so pipeline data stays clean.

**Context:** State machines are everywhere in production — order flows, payment processing, CI/CD pipelines. Implementing one well shows you think about data integrity, not just happy paths.

**Tasks:**
1. `ApplicationStage` enum + `ALLOWED_TRANSITIONS: dict[Stage, set[Stage]]` in `domain/enums.py`.
2. Transition logic lives in the service layer — `if stage not in ALLOWED_TRANSITIONS[app.stage]: raise InvalidTransition(...)`.
3. `PATCH /applications/{id}/stage` validates transitions; invalid ones return 409.
4. `status_changes`/activity table records the transition atomically with the stage update, in the same transaction.

**Acceptance Criteria:**
- `SAVED → INTERVIEW` is rejected (must go through `APPLIED` first).
- Valid transitions succeed and create an audit record.
- `GET /applications/{id}` includes the activity/status history.

**Learning Checkpoint:** Why use an explicit transition map instead of allowing any status change? What bugs does this prevent?

---

### Day 4 — Company Model + Relationships

**Goal:** Separate company data from applications so you can apply to the same company multiple times.

**Context:** Normalization matters. If you store company name as a string on every application, you'll have "Google", "Google Inc.", "Alphabet/Google" as separate entries. Clean data modeling is a signal interviewers look for.

**Tasks:**
1. `Company` model: `id`, `name`, `website`, `industry`, `size` (enum: startup/mid/enterprise), `location`, `notes`, `created_at`.
2. SQLAlchemy model + migration. `Application` gets a `company_id` FK (nullable for now).
3. Repository + service + router following the same pattern as Day 2.
4. `GET /companies/{id}/applications` — list all applications for a company.
5. Application creation accepts either `company_id` or inline `company_name` (service auto-creates or links).

**Acceptance Criteria:**
- Two applications for the same company link to the same company record.
- Deleting a company with applications returns 409 (not cascade delete).
- Company list supports case-insensitive search by name.

**Stretch:** `contacts` table linked to companies (recruiter name, email, LinkedIn, notes).

**Learning Checkpoint:** What's the tradeoff between cascade delete and restrict on FK constraints? When would you choose each?

---

### Day 5 — Testing Foundation + Search/Filter/Sort ✅ (testing part)

**Goal:** Test infrastructure that makes writing tests easy, plus real query capabilities on the application list.

**Context:** Untested portfolio projects are a red flag. Every production API also needs filtering — this is where you demonstrate query-optimization awareness, a common interview topic.

**Tasks (testing — done):**
1. `pytest` + `httpx` test client, transactional-rollback-per-test pattern (each test runs inside a rolled-back transaction, no schema recreation needed).
2. Tests for CRUD happy paths, validation errors, status transitions (valid + invalid).
3. Domain layer tests: status machine as pure functions, no DB needed.
4. GitHub Actions CI running lint + tests on push/PR.

**Tasks (filtering/sorting — remaining):**
5. Extend `GET /applications` with query params: `status`, `company_name`, `date_from`, `date_to`, `search` (across company/title).
6. Sorting: `sort_by` + `sort_order`.
7. Pagination: `page` + `per_page` (default 20, max 100), response includes `total`/`page`/`per_page`/`pages`.
8. DB index on `status`, composite index on `(status, applied_at)`.

**Acceptance Criteria:**
- `make test` runs all tests in < 30 seconds; domain tests need no DB/Docker.
- Filter by status returns only matching applications; pagination metadata is correct.

**Stretch:** PostgreSQL full-text search (`tsvector`) instead of `ILIKE` for search.

**Learning Checkpoint:** When does `ILIKE '%term%'` become a problem? At what table size would you switch to full-text search or an external search engine?

---

## Phase 2: Authentication (Days 6–7)

### Day 6 — AWS Cognito Setup + JWT Verification ✅

**Goal:** Real AWS authentication, not mock auth. First AWS service.

**Context:** Most Swiss companies use OAuth2/OIDC for auth. Cognito is AWS's managed identity service. Setting it up properly — with real JWT verification, not just trusting tokens — is a critical skill.

**Tasks:**
1. Cognito User Pool: email as username, password policy, self-registration enabled, App Client with Authorization Code flow.
2. `core/security/cognito_jwt.py`: fetch + cache JWKS (30-min TTL), verify signature (RS256), expiry, audience, issuer.
3. `GET /auth/me` returns decoded token claims, protected by `require_id_token_payload`.

**Acceptance Criteria:**
- No token → 401. Expired token → 401. Valid token → user info (`sub`, `email`).
- JWKS fetched once and cached, not on every request.

**Learning Checkpoint:** Why verify the JWT signature on the backend instead of just decoding it? What attack does signature verification prevent?

---

### Day 7 — Internal User Model + Route Protection + Essential Error Handling 🟨

**Goal:** Map Cognito users to internal user records, scope all data per user, and stop leaking raw exceptions.

**Context:** External identity providers give you authentication; your app needs its own user table for authorization and relationships. This day also closes the current gap: `get_current_user_id()` is a hardcoded stub — real routes need real auth.

**Tasks:**
1. ✅ `User` model: `id`, `cognito_sub` (unique), `email`, `created_at`. *(Already exists.)*
2. ✅ Replace the `get_current_user_id()` stub with `get_current_user` from `core/security/deps.py` on every application/company/activity route — this dependency verifies the JWT, then looks up or creates (`get_or_create`) the internal user by `cognito_sub`. *(Done 2026-08-14, verified manually against live Cognito.)*
3. ✅ Confirm all repositories already filter by `user_id` (they do) — a user can never see another user's data, even by guessing UUIDs.
4. ⬜ Global exception handler: map `NotFound` → 404, `Forbidden` → 403, `InvalidTransition` → 409, with a consistent JSON error shape. No stack traces or internal paths in responses. *(Currently done per-route via try/except in each route function, not a global FastAPI exception handler.)*
5. ⬜ Handle the obvious Cognito edge case: JWKS endpoint unreachable → 503, not 500. *(`cognito_jwt.py` still raises a plain 500 on JWKS fetch failure.)*

**Acceptance Criteria:**
- First login auto-creates the internal user record.
- User A cannot see User B's applications.
- All application/company endpoints require authentication; `/health` stays open.
- Every error response follows one consistent JSON structure; no stack traces leak.

**Stretch:** Rate limiting on auth endpoints (`slowapi`). Structured logging (`structlog`) with request-id correlation.

**Learning Checkpoint:** Why use a separate internal user ID instead of the Cognito `sub` as your primary key everywhere? What's the difference between a 401 and a 403 — give an example of each in this app.

---

## Phase 3: AI Integration (Days 8–12)

### Day 8 — Provider-Agnostic LLM Client + Gemini Setup

**Goal:** A robust, provider-agnostic LLM abstraction with Gemini 2.5 Flash as the default provider, swappable via config.

**Context:** Two key insights: (1) the LLM is an unreliable external service — treat it like a flaky third-party API with timeouts, retries, cost monitoring; (2) never hardcode a specific provider — production systems abstract so you can switch on cost, quality, or availability.

**Tasks:**
1. `integrations/llm/base.py`: `LLMProvider` protocol with `complete(system_prompt, user_prompt, model=None, temperature=0.0, max_tokens=1024) -> LLMResponse`.
2. `GeminiProvider` (`google-genai` SDK, `gemini-2.5-flash` default, 30s timeout, exponential-backoff retry).
3. `AnthropicProvider` (`anthropic` SDK, `claude-haiku-4-5-20251001` default) — same interface.
4. `integrations/llm/factory.py`: `get_llm_provider()` reads `LLM_PROVIDER` env var (`gemini` | `anthropic`).
5. `integrations/llm/cost_tracker.py`: log every call (provider, model, tokens, cost, latency) to an `llm_usage` table.
6. `core/config.py`: `LLM_PROVIDER`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `LLM_MODEL`, `LLM_ENABLED`.

**Acceptance Criteria:**
- Call succeeds with Gemini; switching `LLM_PROVIDER=anthropic` uses Claude with zero code changes.
- Timeout after 30s returns a graceful error, not a crash.
- Cost/token usage logged with correct per-provider pricing.
- `LLM_ENABLED=false` skips the call, returns a placeholder.

**Stretch:** Circuit breaker (stop calling after 5 consecutive failures for 5 minutes); automatic fallback to the secondary provider.

**Learning Checkpoint:** Why build a provider abstraction instead of using the Gemini SDK directly? What's the cost of this abstraction, and when is it worth paying?

---

### Day 9 — Job Description Parser

**Goal:** Extract structured data from raw job descriptions using the LLM.

**Context:** This is the core AI feature. Job descriptions are messy, inconsistent text — the LLM turns them into structured, queryable data. Same pattern used in document processing, lead enrichment, compliance systems.

**Tasks:**
1. `ParsedJobDescription` schema: required/nice-to-have skills, seniority, tech stack, languages, years experience, remote policy, salary range, key responsibilities, red flags.
2. `services/jd_parser.py`: system prompt for extraction. Gemini → JSON mode; Anthropic → tool use. Provider-specific structured-output handling lives in each provider implementation; the parser only calls `LLMProvider.complete()`.
3. Validate the response against the Pydantic schema; handle missing/malformed fields.
4. `POST /applications/{id}/parse-jd`: takes raw JD text (pasted or from the application record), calls the parser, stores the result in a `parsed_jd` JSON column.

**Acceptance Criteria:**
- Parse 5 real JDs from jobs.ch/LinkedIn; extracted skills/tech stack are reasonable, not hallucinated.
- Malformed LLM responses don't crash the system.

**Stretch:** Run the same JDs through both Gemini Flash and Claude Haiku, compare extraction quality vs. cost.

**Learning Checkpoint:** Why use structured output modes (JSON mode / tool use) instead of asking the LLM to "return JSON" in the prompt? What failure mode does it prevent?

---

### Day 10 — Profile Matching + Scoring

**Goal:** Score each job against your profile to prioritize where to spend time.

**Context:** When applying to 20+ jobs, you need to triage. This also demonstrates prompt engineering — getting consistent, useful scores from an LLM.

**Tasks:**
1. `domain/profile.py`: your skills, years experience, languages, seniority, preferences (remote, min salary, preferred stack).
2. `services/matcher.py`:
   - **Rule-based scoring** (fast, free, deterministic): skill overlap (0-40), seniority match (0-20), language match (0-15), salary compatibility (0-15), remote policy (0-10).
   - **LLM-enhanced analysis**: fit assessment, gaps to address, cover-letter talking points.
3. Store `match_score` (int) and `match_details` (JSON) on the application.
4. `POST /applications/{id}/score` triggers scoring; `GET /applications` supports `sort_by=match_score`.

**Acceptance Criteria:**
- Rule-based score runs instantly, no API call. LLM analysis adds qualitative insight beyond the number.
- Score breakdown is transparent — user can see why a job scored 72/100.

**Learning Checkpoint:** Why combine rule-based and LLM scoring instead of using only the LLM? What are the tradeoffs of each approach?

---

### Day 11 — Follow-Up Email Generator

**Goal:** Generate context-aware follow-up emails based on application stage and company context.

**Context:** Follow-up emails are high-leverage but tedious to write. An LLM that drafts them — aware of company, role, and process stage — removes the friction. (Sending is out of scope here — SES integration was cut; this generates copy-paste-ready drafts.)

**Tasks:**
1. Email templates per stage in `domain/email_templates.py`: after applying, after screening, after interview, after rejection.
2. `services/email_generator.py`: input is application details + stage + optional context notes; system prompt enforces professional tone, under 150 words, Swiss business culture awareness. Returns subject + body, 2 variants (formal/conversational).
3. `POST /applications/{id}/generate-email`: accepts `stage` and optional `context`, returns both drafts.
4. `generated_emails` table: `id`, `application_id`, `stage`, `subject`, `body`, `variant`, `created_at`, `used`.

**Acceptance Criteria:**
- Generated emails are professional and contextually relevant; both variants are meaningfully different.
- Including context notes noticeably improves the output.
- Emails are stored for later reference.

**Learning Checkpoint:** How do you evaluate whether an LLM-generated email is "good enough"? What criteria would you use?

---

### Day 12 — AI Pipeline Orchestration + Light Guardrails

**Goal:** Wire the AI features into one pipeline, with the minimum guardrails a real system needs.

**Context:** The real value is in orchestration — add a JD, and the system parses, scores, and drafts a follow-up automatically. Production AI systems also need basic protection against runaway cost and garbage output — this day keeps that minimal but real.

**Tasks:**
1. `services/pipeline.py`: `process_new_application(application_id)` — parse JD → store → score against profile → store → if score above threshold, generate a follow-up draft. Each step independent: a failure in scoring doesn't lose the parsed JD.
2. Make this a background task triggered on application creation (simple `BackgroundTasks`, no queue infra needed at this scope).
3. **Caching**: hash `(JD text + prompt version + provider)` → return cached result if it exists, stored in an `llm_cache` table. Prevents re-paying for the same JD.
4. **Basic cost budgeting**: `daily_cost_limit` config; check today's spend before each call; clear error (not a crash) if over budget.
5. **Output validation**: parsed JD skills list not empty, seniority is a valid enum, match score within 0-100. One retry with a stricter prompt on invalid output.

**Acceptance Criteria:**
- Creating an application with a JD triggers the full pipeline; each step's result persists independently.
- Parsing the same JD twice returns the cached result (no second API call).
- Exceeding the daily budget returns a clear error, not a crash.

**Stretch:** Prompt versioning + a benchmark comparison across providers (the original Day 19's full tooling) — good if time allows, not required for the core story.

**Learning Checkpoint:** Why cache by hash of (input + prompt version + provider) instead of just input? What's the difference between orchestration and choreography — which are you using here?

---

## Phase 4: AWS Deployment (Days 13–16)

> **Cost management:** the NAT Gateway (~$32-35/mo) and ALB (~$16-20/mo) are the real cost risks here, not CloudWatch (basic Logs usage stays in the Always Free tier). Treat the stack as demo-on-demand: `terraform apply` before a review/interview/demo, `terraform destroy` right after, rather than leaving it running 24/7. This is also a legitimate interview answer, not just a cost hack — it shows deliberate cost control during dev.

### Day 13 — Terraform Foundations: VPC + RDS + Secrets Manager

**Goal:** Network layer and managed database, as code.

**Context:** Every Swiss company doing AWS uses IaC. This day covers VPC fundamentals (public/private subnets, NAT, security groups) and RDS with proper secret handling — both come up in nearly every backend interview.

**Tasks:**
1. `infra/` with `main.tf`, `vpc.tf`, `variables.tf`, `outputs.tf`, `terraform.tfvars` (gitignored).
2. VPC: 2 public subnets (ALB), 2 private subnets (ECS, RDS), NAT Gateway, Internet Gateway.
3. Security groups: ALB (80/443 from anywhere), App (only from ALB SG), DB (5432 only from App SG).
4. RDS PostgreSQL 16, `db.t3.micro`, private subnets, automated backups, encryption at rest.
5. Secrets Manager: DB credentials via `random_password`, never in Terraform state or plain env vars.
6. Run Alembic migrations against RDS from your local machine (CI/CD handles this later).

**Acceptance Criteria:**
- `terraform plan`/`apply` produce the expected VPC, subnets, gateways, security groups, RDS instance.
- DB not reachable from the internet — only from the app security group.
- Credentials live in Secrets Manager, not Terraform state.

**Learning Checkpoint:** Why put the database in a private subnet? Why is Terraform state not a safe place for credentials?

---

### Day 14 — ECR + ECS Fargate Deployment

**Goal:** Containerize and deploy the FastAPI app to ECS Fargate.

**Context:** Fargate is serverless containers — no EC2 management. Understanding task definitions, services, and ALB target groups is essential for any AWS backend role.

**Tasks:**
1. ECR repository; build, tag, push the Docker image.
2. `ecs.tf`: cluster, task definition (256 CPU / 512 MB, env vars from Secrets Manager), service (1 desired task, private subnets, App SG), task execution role (pull image, read secrets) + task role (future S3/other access).
3. `alb.tf`: ALB in public subnets, target group, listener on 80, health check on `/health`.

**Acceptance Criteria:**
- ALB URL returns `{"status": "ok", "db": true}`.
- App connects to RDS through private networking; container logs appear in CloudWatch.
- Stopping the task triggers automatic replacement.

**Learning Checkpoint:** What's the difference between the task execution role and the task role? Why does ECS need both?

---

### Day 15 — S3 for Document Storage

**Goal:** Store CVs/cover letters/documents in S3 directly — no local-storage step first.

**Context:** S3 is the standard object store on AWS. This teaches presigned URLs (a common interview question), bucket policies, and a clean storage abstraction.

**Tasks:**
1. `s3.tf`: private bucket, versioning, server-side encryption, block all public access.
2. `Document` model: `id`, `application_id`, `filename`, `content_type`, `size_bytes`, `s3_key`, `document_type`, `uploaded_at`.
3. `StorageBackend` protocol with `upload`/`download`/`delete`; `S3Storage` implementation.
4. Upload flow: API receives file → streams to S3 → stores S3 key in DB. Download: presigned URL (15-min expiry). Delete: S3 + DB atomically.
5. ECS task role scoped to this bucket only.

**Acceptance Criteria:**
- Upload a PDF via API → appears in S3; download uses a presigned URL, not direct access.
- File size/type validation: 10MB max, pdf/docx/png/jpg only.

**Learning Checkpoint:** Why use presigned URLs instead of proxying the file through your API? What are the tradeoffs?

---

### Day 16 — CI/CD Pipeline + Essential Structured Logging

**Goal:** Automated build/test/deploy on push to main, plus logs that are actually searchable.

**Context:** No production system should require manual deployment. This is non-negotiable in professional environments, and GitHub Actions is the common choice for Swiss startups/mid-size companies. Structured logging is the cheapest piece of observability that pays for itself immediately.

**Tasks:**
1. `.github/workflows/deploy.yml`: lint → test (with Postgres service container) → build image → push to ECR → update ECS service. Triggered on push to `main`.
2. `.github/workflows/pr.yml`: lint + test only, no deploy.
3. Dedicated deploy IAM user, minimal permissions (ECR push + ECS update only). GitHub secrets for AWS credentials.
4. `structlog` JSON logging: timestamp, level, request_id, user_id (if authenticated), endpoint, latency. CloudWatch Log Group with 30-day retention.

**Acceptance Criteria:**
- Push to main triggers build → test → deploy automatically; failed tests block deployment.
- PR checks show green/red status.
- Logs are structured JSON, searchable in CloudWatch by request_id.

**Stretch:** Skip CloudWatch alarms/dashboards (extra cost, AWS-only signal) in favor of Prometheus/Grafana — add a `/metrics` endpoint via `prometheus_client`, then run Prometheus + Grafana locally via `docker-compose` for screenshots/demo. Zero AWS cost, and provider-agnostic monitoring is a more common JD keyword than CloudWatch dashboards specifically.

**Learning Checkpoint:** Why a dedicated deploy IAM user instead of your personal credentials? Why is request_id correlation important?

---

## Phase 5: Frontend + Wrap-up (Days 17–18)

### Day 17 — Next.js Setup + Auth Flow + Application Dashboard

**Goal:** A minimal frontend that authenticates with Cognito and shows the core application list — proof the system works end-to-end, not a polished product.

**Context:** You're a backend engineer — the frontend needs to prove the system works, not be beautiful.

**Tasks:**
1. `npx create-next-app@latest frontend --typescript --tailwind`; `shadcn/ui` for button/card/table/badge/dialog.
2. Cognito auth: login → Hosted UI → callback exchanges code for tokens → tokens stored in memory (never `localStorage`) → logout clears tokens + Cognito logout.
3. `lib/api.ts`: single API client attaching the Bearer token to every request. Route components never call `fetch` directly.
4. Applications table: company, position, status badge, match score, applied date, actions. Filters (status, search), "Add Application" dialog, status-change dropdown respecting the state machine.

**Acceptance Criteria:**
- Login → Cognito → returns with tokens; authenticated API calls work.
- Refreshing the page doesn't lose the session.
- CRUD + status transitions work through the UI; invalid transitions are disabled, not just rejected server-side.

**Learning Checkpoint:** Why store tokens in memory instead of `localStorage`? What attack does `localStorage` exposure enable?

---

### Day 18 — AI Features UI + Application Detail Page + Wrap-up

**Goal:** Expose the AI features through the UI, and close out the portfolio essentials.

**Context:** This is the day that turns a working backend into something an interviewer can actually see and follow along with.

**Tasks:**
1. Application detail page: overview (company, position, status timeline, match score), parsed-JD tab (skills/stack/seniority as tags), match-breakdown tab (point-by-point score), documents tab.
2. Email generator section: "Generate Follow-Up" button, both variants side by side, copy-to-clipboard.
3. **Wrap-up essentials** (trimmed from the original Day 30):
   - README with architecture diagram (Mermaid) and clear setup instructions.
   - `DECISIONS.md` documenting key architectural choices — including what was cut from the original 30-day plan and why (see "What Was Cut" above — this is genuinely good interview material).
   - Seed 10-15 realistic sample applications for demo purposes.
   - Quick pass: no secrets in git history, CORS restricted to the frontend domain.

**Acceptance Criteria:**
- End-to-end: login → add application → AI pipeline processes it → match score visible → follow-up email generated.
- README and DECISIONS.md are clear enough that a stranger could run the project and understand the tradeoffs.

**Stretch:** The full original Day 30 scope — rate limiting audit, N+1 query review, response caching, LLM_BENCHMARK.md, Loom walkthrough.

**Learning Checkpoint:** If an interviewer asks "what would you do differently if you started over?" — you already have a real answer: the cut list above. If they ask "how would you handle a slow AI response in the UI?" — what loading pattern would you use?

---

## Summary: What You'll Have Built

| Layer | Technologies |
|-------|-------------|
| API | FastAPI, Pydantic, sync + async Python |
| Domain | Pure Python, state machines |
| Data | PostgreSQL, SQLAlchemy, Alembic |
| AI | Provider-agnostic LLM layer (Gemini 2.5 Flash default, Claude Haiku 4.5 fallback), structured extraction, cost tracking, caching |
| Auth | AWS Cognito, OAuth2, JWT verification |
| Infra | Terraform, VPC, RDS, ECS Fargate, ALB, S3 |
| CI/CD | GitHub Actions, ECR, automated deploy |
| Frontend | Next.js, TypeScript, shadcn/ui |

**AWS services touched:** Cognito, RDS, ECS, ECR, ALB, S3, Secrets Manager, CloudWatch, IAM, VPC.

**Portfolio talking points:**
- "I built a layered modular monolith with clean separation of concerns — routes, services, repositories, domain, each only calling downward."
- "The AI pipeline parses job descriptions and scores them against my profile, with rule-based and LLM-based scoring combined deliberately."
- "I built a provider-agnostic LLM layer — Gemini by default, Claude as a swap-in — with caching and cost guardrails."
- "It's deployed to AWS with Terraform — VPC, Fargate, RDS, S3 — with CI/CD pushing to ECS on every merge."
- "I scoped a 30-day plan down to 18 days under a real deadline, and can tell you exactly what I cut and why."

---

## Cost Management Notes

Estimated monthly AWS cost while actively using:
- RDS db.t3.micro: ~$15/month (or free tier)
- ECS Fargate (1 task): ~$10/month
- NAT Gateway: ~$35/month (the expensive one — tear down when not actively developing)
- S3: < $1/month
- Gemini 2.5 Flash API: ~$0.50-2/month (free tier covers most development)

**Tip:** Tear down the NAT Gateway and RDS when not actively working (`terraform destroy -target`). Set AWS Budget alerts at $25 and $50. For AI costs, Gemini's free tier (1,000 requests/day) covers the entire development phase at zero cost.
