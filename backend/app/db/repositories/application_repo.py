from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models.application import Application
from app.domain.enums import ApplicationStage


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
        stmt = select(Application).where(
            Application.user_id == user_id,
        )
        return self.db.scalars(stmt).all()

    def create(
        self,
        *,
        user_id: UUID,
        company: str,
        role_title: str,
        job_url: str | None,
        location: str | None = None,
        salary_range: str | None = None,
    ) -> Application:
        app = Application(
            user_id=user_id,
            company=company,
            role_title=role_title,
            job_url=job_url,
            location=location,
            salary_range=salary_range,
        )
        self.db.add(app)
        return app

    def update_stage(
        self,
        *,
        application: Application,
        stage: ApplicationStage,
    ) -> None:
        application.stage = stage
