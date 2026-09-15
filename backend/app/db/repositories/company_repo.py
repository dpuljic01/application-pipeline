from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.company import Company
from app.domain.enums import CompanySize


class CompanyRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_for_user(self, *, user_id: UUID, company_id: UUID) -> Company | None:
        stmt = select(Company).where(
            Company.id == company_id,
            Company.user_id == user_id,
        )
        return self.db.scalar(stmt)

    def get_by_name_for_user(self, *, user_id: UUID, name: str) -> Company | None:
        stmt = select(Company).where(
            Company.user_id == user_id,
            func.lower(Company.name) == name.strip().lower(),
        )
        return self.db.scalar(stmt)

    def list_for_user(
        self, *, user_id: UUID, search: str | None = None
    ) -> list[Company]:
        stmt = select(Company).where(Company.user_id == user_id)
        if search:
            stmt = stmt.where(func.lower(Company.name).contains(search.strip().lower()))
        return self.db.scalars(stmt.order_by(Company.name)).all()

    def create(
        self,
        *,
        user_id: UUID,
        name: str,
        website: str | None = None,
        industry: str | None = None,
        size: CompanySize | None = None,
        location: str | None = None,
        notes: str | None = None,
    ) -> Company:
        company = Company(
            user_id=user_id,
            name=name,
            website=website,
            industry=industry,
            size=size,
            location=location,
            notes=notes,
        )
        self.db.add(company)
        return company

    def get_or_create_for_user(self, *, user_id: UUID, name: str) -> Company:
        """Case-insensitive find-or-create.

        Called from ApplicationService.create_application as part of a
        single transaction — flushes (not commits) so the new row's id is
        available to the caller immediately, but the caller still owns the
        final commit. This is what makes "two applications, same company
        name" resolve to one Company row instead of silently duplicating.
        """
        existing = self.get_by_name_for_user(user_id=user_id, name=name)
        if existing:
            return existing

        company = self.create(user_id=user_id, name=name.strip())
        self.db.flush()
        return company

    def update(self, *, company: Company, data: dict) -> None:
        for field, value in data.items():
            setattr(company, field, value)

    def delete(self, *, company: Company) -> None:
        self.db.delete(company)
