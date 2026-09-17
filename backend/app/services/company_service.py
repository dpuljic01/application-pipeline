from uuid import UUID

from sqlalchemy.orm import Session

from app.db.repositories.application_repo import ApplicationRepository
from app.db.repositories.company_repo import CompanyRepository
from app.domain.enums import CompanySize
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

    def create_company(
        self,
        *,
        user_id: UUID,
        name: str,
        website: str | None = None,
        industry: str | None = None,
        size: CompanySize | None = None,
        location: str | None = None,
        notes: str | None = None,
    ):
        company = self.repository.create(
            user_id=user_id,
            name=name,
            website=website,
            industry=industry,
            size=size,
            location=location,
            notes=notes,
        )
        self.db.commit()
        self.db.refresh(company)
        return company

    def update_company(self, *, user_id: UUID, company_id: UUID, data: dict):
        company = self.get_company_for_user(user_id=user_id, company_id=company_id)
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
