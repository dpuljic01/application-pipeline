from uuid import UUID
from sqlalchemy.orm import Session

from app.api.schemas.application import ApplicationUpdate
from app.api.schemas.jd_parse import ParsedJobDescription
from app.db.repositories.activity_repo import ActivityRepository
from app.db.repositories.application_repo import ApplicationRepository
from app.db.repositories.company_repo import CompanyRepository
from app.domain.enums import ALLOWED_TRANSITIONS, ActivityType, ApplicationStage
from app.domain.errors import InvalidTransition, NotFound
from app.integrations.llm.base import LLMProvider
from app.services.jd_parser import parse_job_description


class ApplicationService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = ApplicationRepository(db)
        self.activity_repository = ActivityRepository(db)
        self.company_repository = CompanyRepository(db)

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
        company_id: UUID | None = None,
    ):
        # Either an explicit company_id (validated to belong to this user),
        # or auto-create/link by name so a second application for the same
        # company resolves to the same Company row instead of duplicating
        # it. `company` (free text) stays the display value either way.
        if company_id is not None:
            linked_company = self.company_repository.get_for_user(
                user_id=user_id, company_id=company_id
            )
            if not linked_company:
                raise NotFound("Company not found")
        else:
            linked_company = self.company_repository.get_or_create_for_user(
                user_id=user_id, name=company
            )

        app = self.repository.create(
            user_id=user_id,
            company=company,
            company_id=linked_company.id,
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

    def delete_application(
        self,
        *,
        user_id: UUID,
        application_id: UUID,
    ) -> None:
        app = self.repository.get_for_user(
            user_id=user_id,
            application_id=application_id,
        )
        if not app:
            raise NotFound("Application not found")

        self.repository.delete(application=app)
        self.db.commit()

    def parse_jd(
        self,
        *,
        user_id: UUID,
        application_id: UUID,
        llm: LLMProvider,
        jd_text: str,
    ) -> ParsedJobDescription:
        app = self.repository.get_for_user(
            user_id=user_id,
            application_id=application_id,
        )
        if not app:
            raise NotFound("Application not found")

        # JDParseError propagates as-is — the route maps it to an HTTP error.
        parsed = parse_job_description(llm, jd_text)

        self.repository.update(
            application=app,
            data={"parsed_jd": parsed.model_dump(mode="json")},
        )
        self.db.commit()
        self.db.refresh(app)
        return parsed

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
