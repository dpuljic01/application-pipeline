from uuid import UUID
from sqlalchemy.orm import Session

from app.db.repositories.application_repo import ApplicationRepository
from app.domain.enums import ApplicationStage
from app.domain.errors import NotFound
from app.db.mixins import utcnow


class ApplicationService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = ApplicationRepository(db)

    def get_application_for_user(
        self,
        *,
        user_id: UUID,
        application_id: UUID,
    ):
        app = self.repository.get_for_user(
            user_id=user_id,
            application_id=application_id,
        )
        if not app:
            raise NotFound("Application not found")
        return app

    def list_applications_for_user(
        self,
        *,
        user_id: UUID,
    ):
        return self.repository.list_for_user(user_id=user_id)

    def create_application(
        self,
        *,
        user_id: UUID,
        company: str,
        role_title: str,
        job_url: str | None = None,
        location: str | None = None,
        salary_range: str | None = None,
    ):
        app = self.repository.create(
            user_id=user_id,
            company=company,
            role_title=role_title,
            job_url=job_url,
            location=location,
            salary_range=salary_range,
        )

        self.db.commit()
        self.db.refresh(app)
        return app

    def change_stage(
        self,
        *,
        user_id: UUID,
        application_id: UUID,
        stage: ApplicationStage,
    ):
        app = self.repository.get_for_user(
            user_id=user_id,
            application_id=application_id,
        )
        if not app:
            raise NotFound("Application not found")

        # business rule: track stage change time
        if app.stage != stage:
            app.stage = stage
            app.stage_changed_at = utcnow()

        self.db.commit()
        self.db.refresh(app)
        return app
