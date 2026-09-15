from uuid import UUID as PyUUID

from sqlalchemy import Enum, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.domain.enums import CompanySize


class Company(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "companies"

    user_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    website: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(120), nullable=True)
    size: Mapped[CompanySize | None] = mapped_column(
        Enum(CompanySize, name="company_size"), nullable=True
    )
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    applications = relationship(
        "Application",
        back_populates="linked_company",
        # No delete cascade here on purpose: deleting a company with linked
        # applications is a 409 (CompanyHasApplications), checked in
        # CompanyService — never a silent cascade delete of application
        # history. The FK's own ondelete="RESTRICT" is the DB-level backstop.
    )

    __table_args__ = (
        # Case-insensitive uniqueness per user, not just an app-level check:
        # this is what lets ApplicationRepository.get_or_create_for_user()
        # be race-safe against two concurrent requests creating the same
        # company under slightly different casing.
        Index(
            "ix_companies_user_name_lower",
            "user_id",
            text("lower(name)"),
            unique=True,
        ),
    )
