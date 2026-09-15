from uuid import UUID

from sqlalchemy.orm import Session

from app.api.schemas.company import CompanyCreate, CompanyUpdate
from app.db.repositories.application_repo import ApplicationRepository
from app.db.repositories.company_repo import CompanyRepository
from app.domain.errors import CompanyHasApplications, NotFound


class CompanyService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = CompanyRepository(db)
        self.application_repository = ApplicationRepository(db)

    def get_company_for_user(self, *, user_id: UUID, company_id: UUID):
        company = self.repository.get_for_user(user_id=user_id, company_id=company_id)
        if not company:
            raise NotFound("Company not found")
        return company

    def list_companies_for_user(self, *, user_id: UUID, search: str | None = None):
        return self.repository.list_for_user(user_id=user_id, search=search)

    def list_applications_for_company(self, *, user_id: UUID, company_id: UUID):
        # Confirms the company exists (and belongs to this user) first, so a
        # bad id 404s instead of silently returning an empty list.
        self.get_company_for_user(user_id=user_id, company_id=company_id)
        return self.application_repository.list_for_company(
            user_id=user_id, company_id=company_id
        )

    def create_company(self, *, user_id: UUID, payload: CompanyCreate):
        company = self.repository.create(
            user_id=user_id,
            name=payload.name,
            website=str(payload.website) if payload.website else None,
            industry=payload.industry,
            size=payload.size,
            location=payload.location,
            notes=payload.notes,
        )
        self.db.commit()
        self.db.refresh(company)
        return company

    def update_company(
        self, *, user_id: UUID, company_id: UUID, payload: CompanyUpdate
    ):
        company = self.get_company_for_user(user_id=user_id, company_id=company_id)

        data = payload.model_dump(exclude_unset=True)
        if data.get("website") is not None:
            data["website"] = str(data["website"])

        self.repository.update(company=company, data=data)
        self.db.commit()
        self.db.refresh(company)
        return company

    def delete_company(self, *, user_id: UUID, company_id: UUID) -> None:
        company = self.get_company_for_user(user_id=user_id, company_id=company_id)

        if self.application_repository.has_for_company(company_id=company.id):
            raise CompanyHasApplications(
                "Cannot delete a company with linked applications"
            )

        self.repository.delete(company=company)
        self.db.commit()
