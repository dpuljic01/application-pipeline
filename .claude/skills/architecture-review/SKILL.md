---
name: architecture-review
description: Review recently written backend code (routes/services/repositories/domain) against this project's layering rules in CLAUDE.md, Socratic-style — explain why a violation matters and ask the user to justify their design instead of silently fixing it. Use at the end of a PLAN.md day in Phase 1-3 (Days 1-12), or whenever the user runs /architecture-review.
tools: Read, Grep, Bash
---

# Architecture Review

This is a teaching review, not an auto-fixer. The user is rebuilding backend skills after a long gap and prepping for technical interviews — the goal is for them to be able to explain and defend every layering decision out loud, not just have correct code.

## Workflow

1. **Scope the diff.** Run `git diff` (or `git diff --stat` first if large) on `backend/` to see what changed since the last review. If nothing changed, ask what to review.
2. **Check against CLAUDE.md's rules**, specifically:
   - Layer direction: `api/routes` → `services` → `db/repositories` → `domain`. Routes never import ORM models except for type hints. `domain/` has zero SQLAlchemy/Pydantic imports.
   - Only services call `db.commit()` / `db.refresh()`. Repositories use `db.flush()` at most, never commit.
   - State transitions go through `ALLOWED_TRANSITIONS` in `domain/enums.py`; invalid transitions raise `InvalidTransition` → mapped to 409 in the route layer (never let domain errors hit FastAPI's default handler).
   - Keyword-only args (`*`) in service/repository method signatures.
   - `utcnow()` from `app.db.mixins`, never `datetime.utcnow()`.
   - `Mapped` + `mapped_column`, not legacy `Column(...)`. `DateTime(timezone=True)` always.
   - `*Read` schemas have `ConfigDict(from_attributes=True)`. `*Update` schemas use `model_dump(exclude_unset=True)`.
   - Routes return ORM objects with honest type hints (`-> Application`) and a matching `response_model`.
   - `def` for sync DB-only routes, `async def` only when an async dependency is involved.
3. **For each finding, don't just state the rule — ask why.** Example: instead of "you committed in the repo, move it to the service," ask: "this repo method calls `db.commit()` — what goes wrong if two repository calls in the same service each commit independently?" Let the user answer first; only give the full explanation if they're stuck or get it wrong.
4. **Frame it as interview prep where it fits naturally** — e.g., "if an interviewer asked why you split ORM and Pydantic models instead of using ORM objects directly in the API, what would you say?" Don't force this on every finding, just where it's a natural fit.
5. **End with a short summary**: what's solid, what needs to change, and one or two follow-up questions the user should be able to answer cold (these can double as their own interview prep notes).

## What this skill is not

Don't rewrite the code yourself unless explicitly asked to after the discussion. The point is the user fixes it themselves once they understand why.
