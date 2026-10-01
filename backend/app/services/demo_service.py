"""Shared demo account: wipes and re-seeds the demo user's data from
demo_seed.json (see scripts/generate_demo_seed.py) on demo login.

Seeding never calls the LLM - every parsed JD and match breakdown in the
seed file is frozen real model output. Dates are stored as "days ago" and
resolved against the current time, so the demo never goes stale (follow-up
badges, "stage since" columns, and the timeline always look recent).
"""

import json
import threading
from datetime import datetime, timedelta
from functools import cache
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.mixins import utcnow
from app.db.repositories.activity_repo import ActivityRepository
from app.db.repositories.application_repo import ApplicationRepository
from app.db.repositories.company_repo import CompanyRepository
from app.db.repositories.profile_repo import ProfileRepository
from app.db.repositories.user_repo import UserRepository
from app.domain.enums import ActivityType, ApplicationStage, PipelineStatus

SEED_PATH = Path(__file__).with_name("demo_seed.json")

# Don't re-seed if the last reset was this recent - otherwise a second
# visitor logging in would wipe the first one's session mid-click. In-memory
# on purpose: one Render instance, and a restart (or free-tier spin-down)
# just means the next demo login seeds fresh, which is the desired state.
RESET_COOLDOWN = timedelta(minutes=15)
_last_reset: datetime | None = None
_lock = threading.Lock()


def is_demo_email(email: str | None) -> bool:
    return bool(
        email and settings.DEMO_EMAIL and email.lower() == settings.DEMO_EMAIL.lower()
    )


def user_daily_llm_budget(db: Session, *, user_id: UUID) -> float | None:
    """Per-user LLM cap for this user, or None for no cap beyond the global
    one. Only the shared demo account has one."""
    user = UserRepository(db).get(user_id=user_id)
    if user is not None and is_demo_email(user.email):
        return settings.LLM_DEMO_DAILY_BUDGET_USD
    return None


@cache
def load_seed() -> dict:
    return json.loads(SEED_PATH.read_text())


class DemoService:
    def __init__(self, db: Session):
        self.db = db
        self.applications = ApplicationRepository(db)
        self.activities = ActivityRepository(db)
        self.companies = CompanyRepository(db)
        self.profiles = ProfileRepository(db)

    def reset_if_stale(self, *, user_id: UUID) -> bool:
        """Re-seeds unless a reset happened within RESET_COOLDOWN. Returns
        whether it reset."""
        global _last_reset
        with _lock:
            now = utcnow()
            if _last_reset is not None and now - _last_reset < RESET_COOLDOWN:
                return False
            self.reset(user_id=user_id, now=now)
            _last_reset = now
            return True

    def reset(self, *, user_id: UUID, now: datetime | None = None) -> None:
        now = now or utcnow()
        seed = load_seed()

        self.applications.delete_all_for_user(user_id=user_id)
        self.companies.delete_all_for_user(user_id=user_id)

        profile = self.profiles.get_or_create_for_user(user_id=user_id)
        self.profiles.update(profile=profile, data=seed["profile"])

        for spec in seed["applications"]:
            self._seed_application(user_id=user_id, spec=spec, now=now)

        self.db.commit()

    def _seed_application(self, *, user_id: UUID, spec: dict, now: datetime) -> None:
        def ago(days: int) -> datetime:
            return now - timedelta(days=days)

        created_at = ago(spec["created_days_ago"])
        company = self.companies.get_or_create_for_user(
            user_id=user_id, name=spec["company"]
        )
        app = self.applications.create(
            user_id=user_id,
            company=spec["company"],
            company_id=company.id,
            role_title=spec["role_title"],
            job_url=None,
            location=spec["location"],
            salary_range=spec["salary_range"],
        )
        self.db.flush()  # assigns app.id for the activities below

        stage = ApplicationStage.SAVED
        stage_changed_at = created_at
        events: list[datetime] = [created_at]
        for to_stage, days_ago in spec["history"]:
            occurred_at = ago(days_ago)
            self.activities.create(
                application_id=app.id,
                activity_type=ActivityType.STAGE_CHANGE,
                note=f"{stage.value} -> {to_stage}",
                occurred_at=occurred_at,
            )
            stage, stage_changed_at = ApplicationStage(to_stage), occurred_at
            events.append(occurred_at)
        for activity_type, days_ago, note in spec["activities"]:
            self.activities.create(
                application_id=app.id,
                activity_type=ActivityType(activity_type),
                note=note,
                occurred_at=ago(days_ago),
            )
            events.append(ago(days_ago))

        match_details = spec["match_details"]
        if match_details is not None:
            match_details = {**match_details, "scored_at": created_at.isoformat()}

        self.applications.update(
            application=app,
            data={
                "stage": stage,
                "stage_changed_at": stage_changed_at,
                "last_activity_at": max(events),
                "created_at": created_at,
                "updated_at": max(events),
                "parsed_jd": spec["parsed_jd"],
                "match_score": spec["match_score"],
                "match_details": match_details,
                "generated_followup": spec["generated_followup"],
                "pipeline_status": PipelineStatus.COMPLETED
                if spec["parsed_jd"] is not None
                else None,
            },
        )
