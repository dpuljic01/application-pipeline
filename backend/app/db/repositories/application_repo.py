from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models.application import Application
from app.domain.enums import ApplicationStage
from app.db.mixins import utcnow


class ApplicationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_for_user(
        self, *, user_id: UUID, application_id: UUID
    ) -> Application | None:
        stmt = select(Application).where(
            Application.id == application_id,
            Application.user_id == user_id,
        )
        return self.db.scalar(stmt)

    def list_for_user(self, *, user_id: UUID) -> list[Application]:
        # Explicit order, not relying on undefined DB row order: newest
        # saved first, matching the frontend's default sort.
        stmt = (
            select(Application)
            .where(Application.user_id == user_id)
            .order_by(Application.created_at.desc())
        )
        return self.db.scalars(stmt).all()

    def list_for_company(self, *, user_id: UUID, company_id: UUID) -> list[Application]:
        stmt = select(Application).where(
            Application.user_id == user_id,
            Application.company_id == company_id,
        )
        return self.db.scalars(stmt).all()

    def has_for_company(self, *, company_id: UUID) -> bool:
        stmt = (
            select(Application.id).where(Application.company_id == company_id).limit(1)
        )
        return self.db.scalar(stmt) is not None

    def create(
        self,
        *,
        user_id: UUID,
        company: str,
        role_title: str,
        job_url: str | None,
        location: str | None = None,
        salary_range: str | None = None,
        company_id: UUID | None = None,
    ) -> Application:
        app = Application(
            user_id=user_id,
            company=company,
            company_id=company_id,
            role_title=role_title,
            job_url=job_url,
            location=location,
            salary_range=salary_range,
        )
        self.db.add(app)
        return app

    def update(self, *, application: Application, data: dict) -> None:
        for field, value in data.items():
            setattr(application, field, value)

    def delete(self, *, application: Application) -> None:
        self.db.delete(application)

    def update_stage(
        self,
        *,
        application: Application,
        stage: ApplicationStage,
        occurred_at: datetime | None = None,
    ) -> None:
        application.stage = stage
        application.stage_changed_at = occurred_at or utcnow()
