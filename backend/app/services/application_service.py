from uuid import UUID
from sqlalchemy.orm import Session

from app.api.schemas.application import ApplicationUpdate
from app.db.repositories.activity_repo import ActivityRepository
from app.db.repositories.application_repo import ApplicationRepository
from app.domain.enums import ALLOWED_TRANSITIONS, ActivityType, ApplicationStage
from app.domain.errors import InvalidTransition, NotFound


class ApplicationService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = ApplicationRepository(db)
        self.activity_repository = ActivityRepository(db)

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

    def update_application(
        self,
        *,
        user_id: UUID,
        application_id: UUID,
        payload: ApplicationUpdate,
    ):
        app = self.repository.get_for_user(
            user_id=user_id,
            application_id=application_id,
        )
        if not app:
            raise NotFound("Application not found")

        data = payload.model_dump(exclude_unset=True)
        if data.get("job_url") is not None:
            data["job_url"] = str(data["job_url"])

        self.repository.update(
            application=app,
            data=data,
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

        if app.stage == stage:
            return app

        if stage not in ALLOWED_TRANSITIONS[app.stage]:
            raise InvalidTransition(f"Cannot transition from {app.stage} to {stage}")

        from_stage = app.stage

        self.repository.update_stage(
            application=app,
            stage=stage,
        )
        activity = self.activity_repository.create(
            application_id=app.id,
            activity_type=ActivityType.STAGE_CHANGE,
            note=f"{from_stage.value} -> {stage.value}",
        )
        self.db.flush()
        app.last_activity_at = activity.created_at

        self.db.commit()
        self.db.refresh(app)
        return app
