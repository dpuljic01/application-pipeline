# Application Pipeline — Day-by-Day Build Plan

> ~30 working days · 2–3 hours each · Backend-first, AWS deploy, AI integration

---

## How to Use This Document

Each day is a self-contained story. Every story follows this structure:

- **Goal** — what you're building and why it matters
- **Context** — how it connects to real-world systems and interviews
- **Tasks** — concrete steps, ordered
- **Acceptance Criteria** — how you know it's done
- **Stretch** — optional if you have extra time
- **Learning Checkpoint** — question to verify you understood the concept, not just copied code

Work linearly. Each day builds on the previous one. If a day takes longer than 3 hours, stop at a clean commit point and finish it the next session. Don't skip days — the ordering is deliberate.

---

## Phase 1: Core Backend Foundation (Days 1–7)

### Day 1 — Docker + PostgreSQL + Alembic Baseline

**Goal:** Reproducible local dev environment with a real migration workflow.

**Context:** Every production backend needs deterministic database migrations. `docker compose up` should give any developer a working system in under 60 seconds. This is table stakes in Swiss companies — interviewers will check.

**Tasks:**
1. Create `docker-compose.yml` with `postgres:16` and your FastAPI app service.
2. Configure `alembic` with async SQLAlchemy engine. Use `DATABASE_URL` from env vars.
3. Create the initial migration (empty — just proves the pipeline works).
4. Add a health check endpoint: `GET /health` returns `{"status": "ok", "db": true}` (actually pings Postgres).
5. Write a `Makefile` or shell script: `make dev` → builds and starts everything.

**Acceptance Criteria:**
- `docker compose up -d` starts both services, API responds on `localhost:8000`.
- `alembic upgrade head` runs cleanly inside the container.
- `GET /health` returns 200 with db confirmation.

**Stretch:** Add `pg_isready` health check on the Postgres container so FastAPI waits for it.

**Learning Checkpoint:** What's the difference between `alembic upgrade head` and `alembic stamp head`? When would you use each?

---

### Day 2 — Application Model + CRUD Endpoints

**Goal:** Core `Application` model with full CRUD through the API layer.

**Context:** This is the central entity. Get the layering right here and everything else follows. Wrong abstractions here will haunt you for weeks.

**Architecture Decision — 2-layer model approach (no `domain/models.py`):**

The plan originally called for three layers: pure Python domain models → SQLAlchemy ORM models → Pydantic schemas. For this project, that adds boilerplate without real benefit. Instead we use two layers:

```
db/models/          → SQLAlchemy ORM models (source of truth for DB shape)
api/schemas/        → Pydantic schemas for request/response (ApplicationCreate, ApplicationRead, ApplicationUpdate)
domain/             → Pure Python only: enums, error classes, business rules (no SQLAlchemy, no Pydantic)
```

The key principle is preserved: **never expose ORM models directly in the API**. `ApplicationRead` uses `model_config = ConfigDict(from_attributes=True)` so FastAPI can serialize ORM objects via `response_model` without manual mapping. The three-layer split (ORM → domain dataclass → Pydantic) is worth it when you need multiple storage backends or an extensive unit-testable domain layer — not here.

**Layer responsibilities:**
- **Route**: parse HTTP input, call service, catch domain errors and map to HTTP status codes, return ORM object (FastAPI serializes via `response_model`)
- **Service**: owns business logic and transaction boundaries (`db.commit()` / `db.refresh()` live here)
- **Repository**: owns all data access and ORM field mutations — service never sets ORM attributes directly
- **Domain**: pure Python enums, `ALLOWED_TRANSITIONS` dict, custom exception classes

**Tasks:**
1. Define the SQLAlchemy model in `db/models/application.py`. Fields: `id (UUID)`, `user_id (FK)`, `company`, `role_title`, `job_url`, `location`, `salary_range`, `stage` (enum), `last_activity_at`, `stage_changed_at`, `created_at`, `updated_at`.
2. Define enums in `domain/enums.py` — pure Python, no framework imports.
3. Write the Alembic migration for the `applications` table.
4. Create `db/repositories/application_repo.py` — CRUD methods operating on ORM objects. All field mutations happen here via `setattr` or direct assignment. No commits.
5. Create `services/application_service.py` — orchestration layer. Calls repo methods, owns `db.commit()` and `db.refresh()`. Business logic (e.g. transition validation) lives here.
6. Create `api/routes/applications.py` — `POST /applications`, `GET /applications`, `GET /applications/{id}`, `PUT /applications/{id}`, `PATCH /applications/{id}/stage`.
7. Create `api/schemas/application.py` — `ApplicationCreate`, `ApplicationUpdate` (all fields optional, use `model_dump(exclude_unset=True)` for partial updates), `ApplicationRead` (with `from_attributes=True`).

**Return type annotation convention:**
```python
@router.get("/{id}", response_model=ApplicationRead)
def get_application(...) -> Application:   # honest: returns ORM object, FastAPI serializes via response_model
```

**Acceptance Criteria:**
- All 5 endpoints work via curl/httpie.
- Creating an application with missing required fields returns 422.
- Getting a non-existent UUID returns 404.
- `domain/` has zero SQLAlchemy or Pydantic imports.
- Routes never import from `db/models/` except for type annotations.

**Stretch:** Add pagination to `GET /applications` (offset + limit with total count in response headers).

**Learning Checkpoint:** Why use two layers (ORM + Pydantic) instead of three (domain dataclass + ORM + Pydantic)? When does the third layer pay off?

---

### Day 3 — Application Status Machine

**Goal:** Enforce valid status transitions so your pipeline data stays clean.

**Context:** State machines are everywhere in production — order flows, payment processing, CI/CD pipelines. Implementing one well shows you think about data integrity, not just happy paths.

**Tasks:**
1. Define status enum and `ALLOWED_TRANSITIONS` dict in `domain/enums.py` — pure Python, no framework imports. The transition map is a `dict[Stage, set[Stage]]` keyed by current stage.
2. Keep transition logic in the service layer — `if stage not in ALLOWED_TRANSITIONS[app.stage]: raise InvalidTransition(...)`. No need for a separate `status_machine.py` file at this scale.
3. Add `PATCH /applications/{id}/stage` endpoint that validates transitions.
4. Invalid transitions return `409 Conflict` with a message explaining what transitions are allowed. (`InvalidTransition` domain error → 409, not 400 — it's a state conflict, not a bad request.)
5. Store status history: create a `status_changes` table (`id`, `application_id`, `from_status`, `to_status`, `changed_at`, `note`).
6. Write the Alembic migration for `status_changes`.
7. Service layer records the transition in both tables atomically.

**Acceptance Criteria:**
- `WISHLIST → INTERVIEWING` is rejected (must go through APPLIED first).
- `APPLIED → SCREENING` succeeds and creates a status_changes record.
- `GET /applications/{id}` includes the full status history.

**Stretch:** Add an optional `note` field on status change (e.g., "Recruiter called, scheduling technical round").

**Learning Checkpoint:** Why use an explicit transition map instead of just allowing any status change? What bugs does this prevent?

---

### Day 4 — Company Model + Relationships

**Goal:** Separate company data from applications so you can apply to the same company multiple times.

**Context:** Normalization matters. If you store company name as a string on every application, you'll have "Google", "Google Inc.", "Alphabet/Google" as separate entries. Clean data modeling is a signal interviewers look for.

**Tasks:**
1. Create `Company` domain model: `id (UUID)`, `name`, `website`, `industry`, `size` (enum: startup/mid/enterprise), `location`, `notes`, `created_at`.
2. SQLAlchemy model + migration. `Application` gets a `company_id` FK (nullable for now — backfill later).
3. Repository + service + router following the same pattern as Day 2.
4. `GET /companies/{id}/applications` — list all applications for a company.
5. Update application creation to accept either `company_id` or inline `company_name` (service auto-creates or links).

**Acceptance Criteria:**
- Creating two applications for the same company links to the same company record.
- Deleting a company with applications returns 409 (not cascade delete).
- Company list endpoint supports search by name (case-insensitive `ILIKE`).

**Stretch:** Add a `contacts` table linked to companies (recruiter name, email, LinkedIn, notes).

**Learning Checkpoint:** What's the tradeoff between cascade delete and restrict on FK constraints? When would you choose each?

---

### Day 5 — Testing Foundation

**Goal:** Test infrastructure that makes writing tests easy, not a chore.

**Context:** Untested portfolio projects are a red flag. But what matters is having the right kind of tests. One good integration test is worth ten mocked unit tests for a CRUD API.

**Tasks:**
1. Set up `pytest` + `pytest-asyncio` + `httpx` (for async test client).
2. Create a test database setup: a separate Postgres container or use transactions that rollback.
3. Write a reusable `async_client` fixture that gives you a test client with a clean DB.
4. Write tests for:
   - Application CRUD (happy path + validation errors).
   - Status transitions (valid + invalid).
   - Company-application relationship.
5. Domain layer tests: test the status machine as pure functions (no DB needed).
6. Add `make test` command.

**Acceptance Criteria:**
- `make test` runs all tests in < 30 seconds.
- At least 15 test cases covering happy paths and error cases.
- Domain tests run without any DB or Docker.

**Stretch:** Add a `conftest.py` factory pattern for creating test data (e.g., `create_application(**overrides)`).

**Learning Checkpoint:** Why test the status machine separately from the API? What does this tell you about your architecture?

---

### Day 6 — Documents + File Attachments (Local)

**Goal:** Attach CVs, cover letters, and other files to applications. Local storage first, S3 later.

**Context:** File handling is deceptively complex. You need to think about naming, deduplication, size limits, and content types. Building it locally first means you can iterate fast, then swap the storage backend to S3 without changing the API contract.

**Tasks:**
1. Create `Document` model: `id`, `application_id`, `filename`, `content_type`, `size_bytes`, `storage_path`, `document_type` (enum: CV, COVER_LETTER, JOB_DESCRIPTION, OTHER), `uploaded_at`.
2. Migration + repo + service.
3. `POST /applications/{id}/documents` — multipart upload. Store in `./uploads/{application_id}/{uuid}_{filename}`.
4. `GET /applications/{id}/documents` — list documents for an application.
5. `GET /documents/{id}/download` — stream the file back.
6. `DELETE /documents/{id}` — removes file + DB record.
7. Add file validation: max 10MB, allowed types (pdf, docx, png, jpg).

**Acceptance Criteria:**
- Upload a PDF, download it back, file is identical.
- Uploading a 20MB file returns 413.
- Uploading a .exe returns 415.
- Deleting a document removes both the DB record and the file.

**Stretch:** Add a `hash` column (SHA-256) and reject duplicate uploads for the same application.

**Learning Checkpoint:** Why store files outside the database? When might you store files in the DB instead?

---

### Day 7 — Search, Filtering, and Sorting

**Goal:** Make the application list actually usable with real query capabilities.

**Context:** Every production API needs filtering. This is also where you demonstrate you understand query optimization — a common interview topic.

**Tasks:**
1. Extend `GET /applications` with query params: `status`, `company_name`, `position_title`, `date_from`, `date_to`, `salary_min`, `search` (full-text across multiple fields).
2. Add sorting: `sort_by` (applied_at, created_at, company_name, salary_max) + `sort_order` (asc/desc).
3. Implement proper pagination with `page` + `per_page` (default 20, max 100).
4. Response includes `total`, `page`, `per_page`, `pages` metadata.
5. Add a DB index on `status` and a composite index on `(status, applied_at)`.
6. Write the migration for indexes.

**Acceptance Criteria:**
- Filter by status returns only matching applications.
- Search "backend" finds applications with "backend" in title or company name.
- Pagination metadata is correct (total count matches filters).
- Sorting by salary descending works.

**Stretch:** Add PostgreSQL full-text search using `tsvector` instead of `ILIKE` for the search parameter.

**Learning Checkpoint:** When does `ILIKE '%term%'` become a problem? At what table size would you switch to full-text search or an external search engine?

---

## Phase 2: Authentication + Authorization (Days 8–10)

### Day 8 — AWS Cognito Setup + JWT Verification

**Goal:** Real AWS authentication, not mock auth. This is your first AWS service.

**Context:** Most Swiss companies use OAuth2/OIDC for auth. Cognito is AWS's managed identity service. Setting it up properly — with proper JWT verification, not just trusting tokens — is a critical skill.

**Tasks:**
1. Create an AWS account if you don't have one. Set up MFA immediately.
2. Create a Cognito User Pool via AWS Console (learn the UI first, automate later):
   - Email as username.
   - Password policy: 8+ chars, mixed case, numbers.
   - Enable self-registration (for your own testing).
   - Create an App Client with Authorization Code flow.
3. Register yourself as a user and get tokens via the Cognito Hosted UI.
4. In FastAPI, create `core/auth.py`:
   - Fetch Cognito JWKS (JSON Web Key Set) on startup, cache it.
   - Create a dependency `get_current_user` that extracts + verifies the JWT from the `Authorization: Bearer` header.
   - Verify: signature (RS256), expiry, audience, issuer.
5. Create a `GET /me` endpoint that returns the decoded token claims.

**Acceptance Criteria:**
- Calling `/me` without a token returns 401.
- Calling `/me` with an expired token returns 401.
- Calling `/me` with a valid token returns user info (sub, email).
- JWKS is fetched once and cached, not on every request.

**Stretch:** Add token refresh logic — accept a refresh token and return new access/id tokens.

**Learning Checkpoint:** Why verify the JWT signature on the backend instead of just decoding it? What attack does signature verification prevent?

---

### Day 9 — Internal User Model + Route Protection

**Goal:** Map Cognito users to internal user records and scope all data per user.

**Context:** External identity providers give you authentication. Your app needs its own user table for authorization, preferences, and relationships. The mapping between external ID (Cognito `sub`) and internal user ID is a pattern you'll see everywhere.

**Tasks:**
1. Create `User` model: `id (UUID)`, `cognito_sub (unique)`, `email`, `name`, `created_at`, `last_login_at`.
2. Migration + repo.
3. Update `get_current_user` dependency: after JWT verification, look up or create the internal user (upsert by `cognito_sub`).
4. Add `user_id` FK to `applications`, `companies`, `documents` tables. Migration with nullable first.
5. Update all repositories to filter by `user_id` — a user can never see another user's data.
6. Update all routers to pass `current_user` from the dependency.
7. Write a backfill migration or script for existing test data.

**Acceptance Criteria:**
- First login creates the internal user record automatically.
- User A cannot see User B's applications (even by guessing UUIDs).
- All existing endpoints still work but now require authentication.
- `/health` remains unauthenticated.

**Stretch:** Add middleware that logs `user_id` on every authenticated request for audit trailing.

**Learning Checkpoint:** Why use a separate internal user ID instead of the Cognito `sub` as your primary key everywhere?

---

### Day 10 — Auth Hardening + Error Handling

**Goal:** Production-grade error handling and auth edge cases.

**Context:** The difference between a demo and a production system is how it handles errors. This day is about closing gaps that interviewers will probe: what happens when Cognito is down? What do your error responses look like? Are you leaking internal details?

**Tasks:**
1. Create a global exception handler in `core/exceptions.py`:
   - Custom exception classes: `NotFoundError`, `ForbiddenError`, `ConflictError`, `ValidationError`.
   - Map each to proper HTTP status codes.
   - Error response format: `{"error": {"code": "NOT_FOUND", "message": "...", "details": {...}}}`.
   - Never leak stack traces or internal paths in production.
2. Handle Cognito edge cases:
   - JWKS endpoint unreachable → return 503 with retry-after.
   - Token from wrong user pool → 401.
   - Token with missing required claims → 401.
3. Add rate limiting on auth endpoints (use `slowapi` or simple middleware).
4. Write tests for all error scenarios.
5. Add structured logging (`structlog`) with request_id correlation.

**Acceptance Criteria:**
- Every error response follows the same JSON structure.
- Cognito failure returns 503, not 500.
- Logs include request_id, user_id (if authenticated), endpoint, and status code.
- No stack traces in error responses.

**Stretch:** Add request timing middleware that logs slow requests (> 500ms).

**Learning Checkpoint:** What's the difference between a 401 and a 403? Give an example of each in this application.

---

## Phase 3: Background Tasks + Reminders (Days 11–13)

### Day 11 — Background Task Infrastructure

**Goal:** Set up async background task processing for operations that shouldn't block API responses.

**Context:** Production APIs don't do heavy work in request handlers. Email sending, PDF generation, AI calls — all of these should be async. Starting with a simple in-process approach, you'll move to a proper task queue on AWS later.

**Tasks:**
1. Set up `arq` (async Redis-based task queue) or `celery` with Redis as broker.
2. Add Redis to `docker-compose.yml`.
3. Create `core/tasks.py` — base task infrastructure with retry logic and error handling.
4. Create your first background task: `send_reminder_email` (for now, just log it — actual email comes later).
5. Create a task status tracking table: `task_logs` — `id`, `task_name`, `status` (PENDING/RUNNING/SUCCESS/FAILED), `payload`, `result`, `created_at`, `completed_at`, `error`.
6. Add `GET /admin/tasks` endpoint to view task history.

**Acceptance Criteria:**
- Triggering a task returns immediately with a task ID.
- Task runs in background and status is tracked in DB.
- Failed tasks are retried (configurable: 3 attempts, exponential backoff).
- Task log shows timing and error details.

**Stretch:** Add a dead-letter mechanism — tasks that fail all retries are marked for manual review.

**Learning Checkpoint:** Why use a task queue instead of just `asyncio.create_task()`? What happens to fire-and-forget tasks when the server restarts?

---

### Day 12 — Reminder Rules Engine

**Goal:** Configurable rules that automatically create follow-up reminders based on application status and timing.

**Context:** This is the "smart" part of your pipeline. Instead of manually remembering to follow up, the system watches your applications and nudges you. Rule engines are common in production systems (billing, notifications, compliance).

**Tasks:**
1. Create `Reminder` model: `id`, `application_id`, `user_id`, `type` (FOLLOW_UP, DEADLINE, CUSTOM), `message`, `due_at`, `status` (PENDING/SENT/DISMISSED), `created_at`.
2. Create `ReminderRule` model: `id`, `user_id`, `trigger_status`, `delay_days`, `message_template`, `is_active`.
3. Default rules (seeded for new users):
   - APPLIED → 7 days → "Follow up on your application to {company_name}"
   - SCREENING → 3 days → "Prepare for screening with {company_name}"
   - INTERVIEWING → 1 day → "Interview prep reminder for {position_title} at {company_name}"
4. Create a periodic task (runs every hour) that:
   - Finds applications where `status_changed_at + delay_days <= now`.
   - Checks if a reminder already exists for that rule + application.
   - Creates new reminders if needed.
5. CRUD endpoints for rules: `GET/POST/PUT/DELETE /reminder-rules`.
6. CRUD endpoints for reminders: `GET /reminders`, `PATCH /reminders/{id}` (dismiss).

**Acceptance Criteria:**
- Moving an application to APPLIED auto-creates a reminder 7 days later.
- Changing status cancels outdated reminders and triggers new ones.
- Users can customize their rules.
- Duplicate reminders are never created.

**Stretch:** Add reminder priority (LOW/MEDIUM/HIGH) and let rules set it based on conditions.

**Learning Checkpoint:** How would you test a time-dependent system like this without waiting 7 actual days? What's the pattern called?

---

### Day 13 — Email Notifications via SES

**Goal:** Send actual reminder emails using AWS SES.

**Context:** This is AWS service number two. SES is how production systems send transactional email. Understanding deliverability, templates, and sandbox mode is practical knowledge you'll use on the job.

**Tasks:**
1. Set up AWS SES:
   - Verify your email address (sandbox mode is fine).
   - Understand sandbox limitations (can only send to verified addresses).
2. Create `integrations/email.py`:
   - Async SES client using `aiobotocore`.
   - `send_email(to, subject, body_html, body_text)` function.
   - Retry logic for SES throttling.
3. Create email templates for each reminder type (simple HTML — doesn't need to be pretty).
4. Wire the reminder task to actually send emails when a reminder's `due_at` is reached.
5. Track delivery: update reminder status to SENT after successful send.
6. Add `EMAIL_ENABLED` env var — when false, log instead of sending (for local dev).

**Acceptance Criteria:**
- Reminder emails are actually received in your inbox.
- Failed sends are retried and logged.
- Local dev doesn't try to hit SES.
- Email contains the right application details (company, position, stage).

**Stretch:** Add email open tracking via a 1x1 pixel and SES event notifications.

**Learning Checkpoint:** Why does SES have a sandbox mode? What do you need to do to send to any email address?

---

## Phase 4: AI Integration (Days 14–19)

### Day 14 — Provider-Agnostic LLM Client + Gemini Setup

**Goal:** Build a robust, provider-agnostic LLM abstraction layer with Gemini 2.5 Flash as the default provider. The architecture should allow swapping providers via config.

**Context:** This is your first time integrating AI as a feature. Two key insights: (1) the LLM is an unreliable external service — treat it like a flaky third-party API with timeouts, retries, fallbacks, and cost monitoring; (2) never hardcode a specific provider — production systems use abstraction layers so you can switch providers based on cost, quality, or availability. This is how senior engineers approach AI integration.

**Tasks:**
1. Design the provider abstraction in `integrations/llm/`:
   ```python
   # integrations/llm/base.py
   from typing import Protocol

   class LLMProvider(Protocol):
       async def complete(
           self, system_prompt: str, user_prompt: str,
           model: str | None = None, temperature: float = 0.0,
           max_tokens: int = 1024,
       ) -> LLMResponse: ...

   @dataclass
   class LLMResponse:
       content: str
       input_tokens: int
       output_tokens: int
       model: str
       latency_ms: float
   ```
2. Implement `GeminiProvider` in `integrations/llm/gemini.py`:
   - Use `google-genai` Python SDK (`pip install google-genai`).
   - Default model: `gemini-2.5-flash` ($0.15/$0.60 per MTok — ~20x cheaper than Claude Haiku on output).
   - Timeout handling (30s default).
   - Retry with exponential backoff (3 attempts).
   - Response validation — check for empty or malformed responses.
3. Implement `AnthropicProvider` in `integrations/llm/anthropic.py`:
   - Use `anthropic` Python SDK.
   - Default model: `claude-haiku-4-5-20251001` ($1/$5 per MTok).
   - Same interface, same error handling patterns.
4. Create `integrations/llm/factory.py`:
   - `get_llm_provider(provider_name: str) -> LLMProvider` — reads from config.
   - Switch providers via `LLM_PROVIDER` env var (`gemini` | `anthropic`).
5. Create `integrations/llm/cost_tracker.py`:
   - Log every API call: provider, model, input_tokens, output_tokens, cost, latency, timestamp.
   - Store in a `llm_usage` table.
   - Pricing map for both providers (updated from their docs).
6. Create `core/config.py` entries: `LLM_PROVIDER` (default: `gemini`), `GEMINI_API_KEY`, `ANTHROPIC_API_KEY` (optional), `LLM_MODEL` (optional override), `LLM_ENABLED`.
7. Write a simple test: send a job description, get a one-sentence summary, verify cost tracking.

**Acceptance Criteria:**
- LLM call succeeds with Gemini and returns a response.
- Switching `LLM_PROVIDER=anthropic` in env vars uses Claude instead — zero code changes.
- Timeout after 30s returns a graceful error, not a crash.
- Cost and token usage are logged in the database with correct per-provider pricing.
- `LLM_ENABLED=false` skips the API call and returns a placeholder.

**Stretch:** Add a circuit breaker — after 5 consecutive failures, stop calling the API for 5 minutes. Also implement automatic fallback: if the primary provider fails, try the secondary.

**Learning Checkpoint:** Why build a provider abstraction instead of using the Gemini SDK directly? What's the cost of this abstraction, and when is it worth paying?

---

### Day 15 — Job Description Parser

**Goal:** Extract structured data from raw job descriptions using the LLM.

**Context:** This is the core AI feature. Job descriptions are messy, inconsistent text. The LLM turns them into structured data you can query, filter, and compare. This is a real-world NLP extraction task — the same pattern used in document processing, lead enrichment, and compliance systems.

**Tasks:**
1. Define the extraction schema in `domain/models.py`:
   ```python
   @dataclass
   class ParsedJobDescription:
       required_skills: list[str]
       nice_to_have_skills: list[str]
       seniority_level: str  # junior/mid/senior/lead/principal
       tech_stack: list[str]
       languages_required: list[str]  # spoken languages
       years_experience: int | None
       remote_policy: str  # remote/hybrid/onsite
       salary_range: str | None
       key_responsibilities: list[str]
       red_flags: list[str]  # detected issues
   ```
2. Create `services/jd_parser.py`:
   - Build a system prompt that instructs the LLM to extract the schema above.
   - For Gemini: use JSON mode (`response_mime_type="application/json"` with a schema).
   - For Anthropic: use tool use (function calling) to enforce the schema.
   - The parser service calls the provider-agnostic `LLMProvider.complete()` — provider-specific structured output handling lives in each provider implementation.
   - Validate the response against your Pydantic schema (handle missing/malformed fields).
3. Create `POST /applications/{id}/parse-jd` endpoint:
   - Takes the raw job description text (from the application or an uploaded document).
   - Calls the parser service.
   - Stores the parsed result in a `parsed_jd` JSON column on the application.
4. Handle edge cases: very short JDs, non-English JDs, JDs with no clear requirements.

**Acceptance Criteria:**
- Parse 5 real job descriptions from Swiss job boards (jobs.ch, LinkedIn).
- Extracted skills and tech stack are reasonable (not hallucinated).
- Non-English JDs (German) are handled gracefully.
- Malformed LLM responses don't crash the system.

**Stretch:** Run the same 5 JDs through both Gemini Flash and Claude Haiku. Compare extraction quality vs. cost. Document the results — this becomes interview gold.

**Learning Checkpoint:** Why use structured output modes (JSON mode / tool use) instead of asking the LLM to "return JSON" in the prompt? What failure mode does it prevent?

---

### Day 16 — Profile Matching + Scoring

**Goal:** Score each job against your profile to prioritize where to spend time.

**Context:** When you're applying to 20+ jobs, you need to triage. A match score helps you focus effort on high-probability applications instead of spray-and-pray. This is also a practical demonstration of prompt engineering — getting consistent, useful scores from an LLM.

**Tasks:**
1. Create your profile definition in `domain/profile.py`:
   ```python
   MY_PROFILE = {
       "skills": ["Python", "FastAPI", "Django", "PostgreSQL", "Docker", "AWS", ...],
       "years_experience": 5,
       "languages": ["English", "..."],  # add your spoken languages
       "seniority": "mid-senior",
       "preferences": {
           "remote": True,
           "min_salary_chf": 100000,
           "preferred_stack": ["Python", "FastAPI", "PostgreSQL"],
       }
   }
   ```
2. Create `services/matcher.py`:
   - Takes `ParsedJobDescription` + profile.
   - **Rule-based scoring** (fast, free, deterministic):
     - Skill overlap percentage (0-40 points).
     - Seniority match (0-20 points).
     - Language match (0-15 points).
     - Salary range compatibility (0-15 points).
     - Remote policy match (0-10 points).
   - **LLM-enhanced analysis** (deeper, costs money):
     - Send profile + parsed JD to LLM.
     - Ask for: fit assessment, gaps to address, talking points for cover letter.
3. Store scores on the application: `match_score (int)`, `match_details (JSON)`.
4. `POST /applications/{id}/score` — triggers scoring.
5. Update `GET /applications` to support `sort_by=match_score`.

**Acceptance Criteria:**
- Rule-based score runs instantly, no API call.
- LLM analysis adds qualitative insights beyond the numeric score.
- Score breakdown is transparent (user can see why a job scored 72/100).
- Sorting by score puts the best matches first.

**Stretch:** Add a "missing skills" endpoint that aggregates across all parsed JDs to show which skills you should learn.

**Learning Checkpoint:** Why combine rule-based and LLM scoring instead of using only the LLM? What are the tradeoffs of each approach?

---

### Day 17 — Follow-Up Email Generator

**Goal:** Generate context-aware follow-up emails based on the application stage and company context.

**Context:** Follow-up emails are one of the highest-leverage actions in a job search, but people skip them because writing them is tedious. An LLM that drafts them — aware of the company, role, and where you are in the process — removes that friction.

**Tasks:**
1. Define email templates per stage in `domain/email_templates.py`:
   - After applying (1 week): "checking in" email.
   - After screening: thank you + reiterate interest.
   - After interview: personalized thank you with specific discussion points.
   - After rejection: graceful close + networking ask.
2. Create `services/email_generator.py`:
   - Input: application details, company info, stage, optional context notes.
   - System prompt includes: professional tone, concise (under 150 words), Swiss business culture awareness.
   - Returns: subject line + email body.
   - Generate 2 variants: formal and conversational — let the user pick.
3. `POST /applications/{id}/generate-email` endpoint:
   - Accepts `stage` and optional `context` (e.g., "discussed microservices migration in interview").
   - Returns generated email drafts.
4. Store generated emails: `generated_emails` table — `id`, `application_id`, `stage`, `subject`, `body`, `variant`, `created_at`, `used` (boolean).

**Acceptance Criteria:**
- Generated emails are professional and contextually relevant.
- Including context notes produces noticeably better emails.
- Both variants are meaningfully different (not just synonym swaps).
- Emails are stored for later reference.

**Stretch:** Add a "refine" endpoint that takes feedback ("make it shorter", "mention my AWS experience") and regenerates.

**Learning Checkpoint:** How do you evaluate whether an LLM-generated email is "good enough"? What criteria would you use?

---

### Day 18 — AI Pipeline Orchestration

**Goal:** Wire all AI features into a single pipeline that processes a new application end-to-end.

**Context:** Individual AI features are useful but the real value is in orchestration — add a job URL, and the system automatically parses, scores, and queues follow-ups. This is a common pattern in production AI systems: chaining multiple LLM calls with validation between each step.

**Tasks:**
1. Create `services/pipeline.py`:
   - `process_new_application(application_id)` — the master orchestrator:
     1. Extract JD text (from stored document or URL).
     2. Parse JD → store structured data.
     3. Score against profile → store match score.
     4. If score > threshold → auto-generate follow-up email draft.
     5. Create appropriate reminders based on score.
   - Each step is independent — failure in step 3 doesn't block step 2's results.
2. Make this a background task triggered on application creation.
3. Add pipeline status tracking: `pipeline_runs` table — `id`, `application_id`, `steps` (JSON array of step name + status + timing).
4. `GET /applications/{id}/pipeline-status` — shows which steps completed.

**Acceptance Criteria:**
- Creating a new application with a JD triggers the full pipeline.
- Each step's result is persisted independently.
- A failure in scoring still preserves the parsed JD.
- Pipeline status shows timing for each step.

**Stretch:** Add a retry mechanism — `POST /applications/{id}/retry-pipeline?step=score` reruns a specific failed step.

**Learning Checkpoint:** What's the difference between orchestration and choreography in distributed systems? Which pattern are you using here?

---

### Day 19 — AI Quality + Cost Guardrails

**Goal:** Production-grade controls around your AI features — caching, cost limits, quality validation, and provider benchmarking.

**Context:** LLMs are non-deterministic and costs vary wildly across providers. In production, you need guardrails: budget caps, caching to avoid duplicate calls, validation to catch garbage outputs, and data to justify which provider you're using. This is what separates a demo from a system you'd actually deploy.

**Tasks:**
1. **Response caching**: Hash the input (JD text + prompt version + provider) → check if result exists → return cached result. Store in `llm_cache` table.
2. **Cost budgeting**:
   - Add `daily_cost_limit` config (default: $0.50 — generous for Gemini Flash pricing).
   - Before each LLM call, check today's total spend.
   - If over budget, return a clear error (not a crash).
   - `GET /admin/ai/usage` — shows daily/weekly/monthly cost breakdown, broken down by provider and model.
3. **Output validation**:
   - Validate parsed JD: skills list not empty, seniority is a valid enum value.
   - Validate match score: within 0-100 range.
   - Validate emails: not empty, reasonable length, no obvious hallucination markers.
   - Invalid outputs trigger a retry with a stricter prompt.
4. **Prompt versioning**: store prompt templates with version numbers. Log which version + provider + model produced each result.
5. **Provider comparison tooling**:
   - Add a management command: `python -m cli benchmark --jd-file samples.json`.
   - Runs the same 10 JDs through all configured providers.
   - Outputs a comparison table: provider, model, avg latency, avg cost, extraction quality score (based on field completeness).
   - Store results in `llm_benchmarks` table for historical tracking.
6. Write tests with mocked LLM responses (don't spend money on test runs).

**Acceptance Criteria:**
- Parsing the same JD twice returns the cached result (no API call).
- Exceeding the daily budget returns 429 with a clear message.
- Invalid LLM output triggers one retry, then returns a structured error.
- Usage dashboard shows accurate cost data per provider.
- Benchmark command produces a readable comparison of providers.

**Stretch:** Add smart model routing — use Gemini Flash by default, auto-escalate to Claude Haiku or Gemini Pro for complex tasks (e.g., match scoring where the initial result has low confidence). Log which model was used per call to compare quality/cost tradeoffs.

**Learning Checkpoint:** You have benchmark data showing Gemini Flash is 10x cheaper but Claude Haiku extracts 15% more skills from German-language JDs. How do you decide which to use? What framework would you apply?

---

## Phase 5: AWS Deployment (Days 20–26)

### Day 20 — Terraform Foundations + VPC

**Goal:** Define your AWS infrastructure as code. Start with the network layer.

**Context:** Every Swiss company doing AWS uses IaC (Terraform or CDK). Clicking through the console is for learning; Terraform is for building. This day is about understanding VPC fundamentals — public vs. private subnets, NAT gateways, security groups. These concepts come up in literally every backend interview.

**Tasks:**
1. Install Terraform. Create `infra/` directory structure:
   ```
   infra/
     main.tf          # provider config
     vpc.tf           # network
     variables.tf     # input variables
     outputs.tf       # exported values
     terraform.tfvars # your values (gitignored)
   ```
2. Define a VPC with:
   - 2 public subnets (for ALB).
   - 2 private subnets (for ECS tasks, RDS).
   - NAT Gateway (for private subnet internet access).
   - Internet Gateway.
3. Define security groups:
   - ALB SG: allow 80/443 inbound from anywhere.
   - App SG: allow traffic only from ALB SG.
   - DB SG: allow 5432 only from App SG.
4. `terraform plan` and `terraform apply`.
5. Verify in AWS Console that resources match your code.

**Acceptance Criteria:**
- `terraform plan` shows clean, expected changes.
- VPC, subnets, gateways, and security groups exist in AWS.
- Security groups follow least-privilege (DB not accessible from internet).

**Stretch:** Add a bastion host or SSM endpoint for emergency database access.

**Learning Checkpoint:** Why put the database in a private subnet? What would happen if it were in a public subnet with a security group restricting access?

---

### Day 21 — RDS PostgreSQL + Secrets Manager

**Goal:** Managed PostgreSQL on AWS with proper secret handling.

**Context:** RDS is the standard for managed databases on AWS. Understanding parameter groups, backup policies, and secret rotation shows production awareness. Never hardcode database credentials — Secrets Manager is the answer.

**Tasks:**
1. Add `rds.tf`:
   - RDS PostgreSQL 16 instance (db.t3.micro for cost — free tier eligible).
   - Private subnets only (use the DB subnet group from Day 20).
   - Automated backups enabled (7-day retention).
   - Encryption at rest enabled.
2. Add `secrets.tf`:
   - Store DB credentials in AWS Secrets Manager.
   - Generate a random password using `random_password` resource.
3. Create a parameter group with sensible defaults (`log_min_duration_statement = 1000`).
4. Update your app's config to read `DATABASE_URL` from Secrets Manager (not env vars) when running on AWS.
5. Run Alembic migrations against the RDS instance from your local machine (temporary — CI/CD later).

**Acceptance Criteria:**
- RDS instance is running and accessible from the private subnet.
- Cannot connect to RDS from the internet (only from app security group).
- Credentials are in Secrets Manager, not in Terraform state or env vars.
- Alembic migrations run successfully against RDS.

**Stretch:** Enable RDS Performance Insights and look at your query patterns.

**Learning Checkpoint:** What's the difference between `terraform.tfstate` and Secrets Manager for storing secrets? Why is Terraform state not a safe place for credentials?

---

### Day 22 — ECR + ECS Fargate Deployment

**Goal:** Containerize and deploy your FastAPI app to ECS Fargate.

**Context:** Fargate is serverless containers — you don't manage EC2 instances. This is the modern default for container workloads on AWS. Understanding task definitions, services, and ALB target groups is essential for any AWS backend role.

**Tasks:**
1. Create an ECR repository for your Docker image.
2. Build and push your Docker image:
   ```bash
   docker build -t app-pipeline .
   aws ecr get-login-password | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
   docker tag app-pipeline:latest <ecr-repo>:latest
   docker push <ecr-repo>:latest
   ```
3. Add `ecs.tf`:
   - ECS Cluster.
   - Task Definition: your image, 256 CPU / 512 MB memory, env vars from Secrets Manager.
   - Service: 1 desired task (scale later), private subnets, App SG.
   - IAM roles: task execution role (pull image, read secrets) + task role (SES, S3).
4. Add `alb.tf`:
   - Application Load Balancer in public subnets.
   - Target group pointing to ECS service.
   - Listener on port 80 (HTTPS later).
   - Health check: `GET /health`.
5. `terraform apply` and verify the ALB URL returns your health check.

**Acceptance Criteria:**
- ALB URL returns `{"status": "ok", "db": true}`.
- App connects to RDS through private networking.
- Container logs appear in CloudWatch.
- Stopping the task triggers automatic replacement (desired count = 1).

**Stretch:** Add HTTPS with ACM certificate and Route53 domain (if you have a domain).

**Learning Checkpoint:** What's the difference between the task execution role and the task role? Why does ECS need both?

---

### Day 23 — S3 for Document Storage

**Goal:** Move file uploads from local disk to S3, the right way.

**Context:** Local file storage doesn't survive container restarts. S3 is the standard object store on AWS. This day teaches you presigned URLs (a common interview question), bucket policies, and the storage abstraction pattern.

**Tasks:**
1. Add `s3.tf`: create a private S3 bucket with:
   - Versioning enabled.
   - Server-side encryption (AES-256).
   - Block all public access.
   - Lifecycle rule: move to IA after 90 days.
2. Update `services/document_service.py`:
   - Create a `StorageBackend` protocol with `upload`, `download`, `delete` methods.
   - Implement `LocalStorage` (existing) and `S3Storage` (new).
   - Use dependency injection to swap backends based on environment.
3. Upload flow: API receives file → stream to S3 → store S3 key in DB.
4. Download flow: generate a presigned URL (15 min expiry) → redirect client.
5. Delete flow: delete from S3 + DB atomically.
6. Update ECS task role to allow S3 access to this bucket only.

**Acceptance Criteria:**
- Upload a file via API → appears in S3 bucket.
- Download link uses presigned URL (not direct S3 access).
- Presigned URL expires after 15 minutes.
- Local dev still uses local storage (no AWS dependency).

**Stretch:** Add S3 event notification → Lambda that scans uploaded files for viruses (ClamAV).

**Learning Checkpoint:** Why use presigned URLs instead of proxying the file through your API? What are the tradeoffs?

---

### Day 24 — EventBridge for Scheduled Tasks

**Goal:** Replace your local task scheduler with AWS EventBridge for production-grade scheduling.

**Context:** Cron jobs on a container are fragile — if the container restarts, you miss the job. EventBridge is AWS's serverless scheduler. Understanding event-driven architecture is a key skill for senior backend roles.

**Tasks:**
1. Create a new ECS task definition for the "worker" — same image but different command (`python -m worker`).
2. Add `eventbridge.tf`:
   - Rule: trigger every hour → run ECS task (reminder checker).
   - Rule: trigger daily at 9am → run ECS task (daily digest).
   - IAM role for EventBridge to launch ECS tasks.
3. Refactor your reminder check task to work as a standalone script (not tied to the web server process):
   - Accept command-line args or env vars for what to run.
   - Exit cleanly after completion (Fargate bills per-second).
4. Create a daily digest task:
   - Summarize today's reminders + upcoming deadlines.
   - Send via SES.
5. Add CloudWatch alarms: alert if a scheduled task fails.

**Acceptance Criteria:**
- EventBridge triggers the reminder check every hour (verify in CloudWatch logs).
- Daily digest email arrives at 9am with correct summary.
- Failed tasks trigger a CloudWatch alarm.
- Worker tasks exit cleanly (exit code 0).

**Stretch:** Add an EventBridge rule that triggers on application status changes (event-driven, not polling).

**Learning Checkpoint:** What's the difference between EventBridge scheduled rules and ECS scheduled tasks? When would you use one over the other?

---

### Day 25 — CI/CD Pipeline

**Goal:** Automated build, test, and deploy on every push to main.

**Context:** No production system should require manual deployment. CI/CD is non-negotiable in professional environments. GitHub Actions is the most common choice for startups and mid-size companies in Switzerland.

**Tasks:**
1. Create `.github/workflows/deploy.yml`:
   - Trigger: push to `main`.
   - Steps:
     1. Run linting (`ruff`).
     2. Run tests (`pytest`) with a Postgres service container.
     3. Build Docker image.
     4. Push to ECR.
     5. Update ECS service to use the new image.
2. Create `.github/workflows/pr.yml`:
   - Trigger: pull request.
   - Steps: lint + test only (no deploy).
3. Set up GitHub secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`.
4. Create a deploy IAM user with minimal permissions (ECR push + ECS update only).
5. Test the full flow: make a change → push → watch it deploy.

**Acceptance Criteria:**
- Push to main triggers build → test → deploy automatically.
- Failed tests block deployment.
- PR checks show green/red status.
- Deployment completes in under 10 minutes.

**Stretch:** Add Slack notification on deploy success/failure. Add semantic versioning with git tags.

**Learning Checkpoint:** Why create a dedicated deploy IAM user instead of using your personal credentials? What's the principle of least privilege in this context?

---

### Day 26 — Monitoring + Observability

**Goal:** Know when your system is broken before your users tell you.

**Context:** A deployed system without monitoring is a liability. This day covers the three pillars of observability: logs, metrics, and traces. In interviews, asking "how would you monitor this?" is a standard senior-level question.

**Tasks:**
1. **Structured Logging**:
   - Ensure all logs use JSON format with `structlog`.
   - Include: timestamp, level, request_id, user_id, endpoint, latency.
   - Configure CloudWatch Log Groups with 30-day retention.
2. **Metrics**:
   - Add a `/metrics` endpoint with Prometheus-format metrics (or use CloudWatch custom metrics):
     - Request count by endpoint and status code.
     - Request latency (p50, p95, p99).
     - Active database connections.
     - LLM API call count and latency (broken down by provider).
     - Background task success/failure rate.
3. **Alarms**:
   - 5xx error rate > 5% → alarm.
   - API latency p99 > 2s → alarm.
   - ECS task count = 0 → alarm (service down).
   - RDS CPU > 80% → alarm.
   - Daily LLM cost > budget → alarm.
4. Create a CloudWatch dashboard with key metrics.

**Acceptance Criteria:**
- Logs are searchable in CloudWatch with structured fields.
- Dashboard shows real-time request rate, latency, and error rate.
- At least 5 alarms configured and testable.
- Can trace a single request from ALB → app → database using request_id.

**Stretch:** Add distributed tracing with AWS X-Ray.

**Learning Checkpoint:** What's the difference between monitoring and observability? Why is request_id correlation important?

---

## Phase 6: Frontend + Polish (Days 27–30)

### Day 27 — Next.js Setup + Auth Flow

**Goal:** Minimal frontend that authenticates with Cognito and talks to your API.

**Context:** You're a backend engineer — the frontend doesn't need to be beautiful. It needs to prove your system works end-to-end. A working auth flow and a clean data display is enough.

**Tasks:**
1. `npx create-next-app@latest frontend --typescript --tailwind`.
2. Install `shadcn/ui` components: button, card, table, badge, dialog.
3. Implement Cognito auth:
   - Login page → redirect to Cognito Hosted UI.
   - Callback page → exchange code for tokens.
   - Store tokens in memory (not localStorage for security).
   - Logout → clear tokens + Cognito logout.
4. Create an API client (`lib/api.ts`) that attaches the Bearer token to every request.
5. `GET /me` displayed on a simple profile page — proves auth works end-to-end.

**Acceptance Criteria:**
- Login redirects to Cognito, returns with tokens.
- Authenticated API calls work.
- Unauthenticated state shows login button.
- Refreshing the page doesn't lose the session (use refresh tokens).

**Stretch:** Add a loading skeleton and error boundaries.

**Learning Checkpoint:** Why store tokens in memory instead of localStorage? What attack does localStorage exposure enable?

---

### Day 28 — Application Dashboard

**Goal:** The main view — see all your applications with status, score, and actions.

**Context:** This is the page you'll actually use daily. Keep it functional, not flashy.

**Tasks:**
1. Applications table with columns: Company, Position, Status (as colored badge), Match Score, Applied Date, Actions.
2. Filters: status dropdown, search box, sort controls.
3. "Add Application" dialog: company, position, URL, paste JD text.
4. Status change: click badge → dropdown → confirm transition.
5. Match score displayed as a colored bar (red < 40, yellow 40-70, green > 70).
6. Auto-refresh: poll every 30 seconds or use a simple refetch trigger.

**Acceptance Criteria:**
- All CRUD operations work through the UI.
- Status transitions respect the state machine (invalid transitions disabled).
- Filtering and sorting work.
- Adding an application triggers the AI pipeline (visible in status).

**Stretch:** Add drag-and-drop Kanban board view (applications as cards in status columns).

**Learning Checkpoint:** When would you use WebSockets instead of polling for real-time updates? What's the tradeoff?

---

### Day 29 — AI Features UI + Application Detail Page

**Goal:** Expose your AI features through the UI — parsing results, match breakdown, generated emails.

**Tasks:**
1. Application detail page (`/applications/{id}`):
   - Overview card: company, position, status timeline, match score.
   - Parsed JD tab: skills, tech stack, seniority, languages — displayed as tags.
   - Match breakdown tab: score visualization with point-by-point breakdown.
   - Documents tab: upload/download files.
   - Status history tab: timeline of all changes with notes.
2. Email generator section:
   - "Generate Follow-Up" button.
   - Shows both variants side-by-side.
   - "Copy to Clipboard" button.
   - History of generated emails.
3. Reminders section:
   - Upcoming reminders with dismiss/snooze.
   - Link to reminder rules settings.

**Acceptance Criteria:**
- Parsed JD data displays correctly.
- Match score breakdown is understandable.
- Email generation works and shows both variants.
- Can dismiss reminders from the UI.

**Stretch:** Add a "Quick Apply" flow: paste URL → system fetches JD → parses → scores → suggests next action.

**Learning Checkpoint:** How would you handle a slow AI response in the UI? What loading patterns would you use?

---

### Day 30 — Production Hardening + Documentation

**Goal:** Final polish. Make the system production-ready and document everything for your portfolio.

**Context:** This is the day that turns a project into a portfolio piece. Clean documentation, a working demo, and clear architecture diagrams are what make interviewers take you seriously.

**Tasks:**
1. **Security audit**:
   - CORS configuration (restrict to your frontend domain).
   - Rate limiting on all endpoints.
   - Input sanitization review.
   - Verify no secrets in git history (`git-secrets` or `trufflehog`).
2. **Performance**:
   - Add database connection pooling config.
   - Review N+1 queries (use SQLAlchemy eager loading where needed).
   - Add response caching for expensive endpoints (match scores).
3. **Documentation**:
   - Update README with architecture diagram (use Mermaid).
   - API documentation: ensure OpenAPI/Swagger is clean and complete.
   - Add a DECISIONS.md documenting key architectural choices and why.
   - Add a DEPLOYMENT.md with step-by-step setup instructions.
   - Add a LLM_BENCHMARK.md with your provider comparison results from Day 19 — include cost, latency, and quality data.
4. **Demo readiness**:
   - Seed the database with 15-20 realistic sample applications.
   - Ensure the system works end-to-end with real data.
   - Record a 2-minute Loom walkthrough of the key features.

**Acceptance Criteria:**
- System runs end-to-end: login → add application → AI processes it → reminders work → email generated.
- README is comprehensive and professional.
- No secrets in the repository.
- Swagger docs are accurate and include examples.

**Stretch:** Add a cost estimation section: "Running this system costs approximately $X/month on AWS" with breakdown.

**Learning Checkpoint:** If an interviewer asks "what would you do differently if you started over?", what's your answer? Write it in DECISIONS.md.

---

## Summary: What You'll Have Built

| Layer | Technologies |
|-------|-------------|
| API | FastAPI, Pydantic, async Python |
| Domain | Pure Python, state machines, rule engine |
| Data | PostgreSQL, SQLAlchemy, Alembic |
| AI | Provider-agnostic LLM layer (Gemini 2.5 Flash default, Claude Haiku 4.5 fallback), prompt engineering, structured extraction, cost management, provider benchmarking |
| Auth | AWS Cognito, OAuth2, JWT verification |
| Infra | Terraform, VPC, RDS, ECS Fargate, ALB, S3, SES, EventBridge |
| CI/CD | GitHub Actions, ECR, automated deploy |
| Monitoring | CloudWatch, structured logging, alarms |
| Frontend | Next.js, TypeScript, shadcn/ui |

**Total AWS services touched:** Cognito, RDS, ECS, ECR, ALB, S3, SES, EventBridge, Secrets Manager, CloudWatch, IAM, VPC.

**Portfolio talking points:**
- "I built a modular monolith with clean separation of concerns."
- "The AI pipeline parses job descriptions and scores them against my profile."
- "I built a provider-agnostic LLM layer — benchmarked Gemini vs. Claude on extraction quality, latency, and cost, then chose based on data."
- "It's deployed to AWS with Terraform — VPC, Fargate, RDS, the full stack."
- "I implemented background task processing with EventBridge for scheduled jobs."
- "CI/CD is automated — push to main triggers build, test, and deploy."

---

## Cost Management Notes

Estimated monthly AWS cost while actively using:
- RDS db.t3.micro: ~$15/month (or free tier)
- ECS Fargate (1 task): ~$10/month
- NAT Gateway: ~$35/month (this is the expensive one — consider removing when not actively developing)
- S3: < $1/month
- SES: < $1/month
- Gemini 2.5 Flash API: ~$0.50-2/month (free tier covers most development)

**LLM Cost Comparison (per 1M tokens, input/output):**

| Provider / Model | Input | Output | Cost per JD parse* |
|-----------------|-------|--------|-------------------|
| Gemini 2.5 Flash (default) | $0.15 | $0.60 | ~$0.0004 |
| Gemini 2.5 Pro | $1.25 | $10.00 | ~$0.006 |
| Claude Haiku 4.5 | $1.00 | $5.00 | ~$0.003 |
| Claude Sonnet 4.6 | $3.00 | $15.00 | ~$0.009 |

*\*~1,300 input tokens + ~400 output tokens per parse*

At Gemini Flash pricing, parsing 500 job descriptions costs about **$0.20 total**. The Gemini free tier (1,000 requests/day) covers your entire development phase at zero cost.

**Tip:** Tear down the NAT Gateway and RDS when not actively working. Use `terraform destroy -target` for specific resources. Set up AWS Budget alerts at $25 and $50. For AI costs, start with Gemini's free tier during development, then use the paid tier in production — you'll struggle to spend more than $2/month on a personal project.