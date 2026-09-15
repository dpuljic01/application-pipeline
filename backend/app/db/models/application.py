from datetime import datetime

from uuid import UUID as PyUUID
from sqlalchemy import String, DateTime, Enum, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin, TimestampMixin
from app.domain.enums import ApplicationStage


class Application(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "applications"

    user_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    company: Mapped[str] = mapped_column(String(200), nullable=False)
    # Nullable for now (Day 4): free-text `company` above stays the source
    # of truth for existing rows and for display; this FK is populated by
    # ApplicationService going forward (either an explicit company_id, or
    # an auto-created/linked Company resolved from `company` by name).
    company_id: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    role_title: Mapped[str] = mapped_column(String(128), nullable=False)
    job_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    salary_range: Mapped[str | None] = mapped_column(String(100), nullable=True)
    stage: Mapped[ApplicationStage] = mapped_column(
        Enum(ApplicationStage, name="application_stage"),
        nullable=False,
        default=ApplicationStage.SAVED,
        server_default=text("'SAVED'"),
    )

    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stage_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user = relationship("User", back_populates="applications")
    # Named `linked_company`, not `company` — that name is already the
    # existing free-text string column above.
    linked_company = relationship("Company", back_populates="applications")
    activities = relationship(
        "Activity",
        back_populates="application",
        cascade="all, delete-orphan",  # propagate operations from parent, delete-orphan to remove unlinked activities
    )

    __table_args__ = (
        Index("ix_applications_user_last_activity", "user_id", last_activity_at.desc()),
        Index(
            "ix_applications_user_updated_at", "user_id", "updated_at"
        ),  # No need for DESC magic, postgres can perform backward scans on B-tree indexes, meaning ASC index supports both sort directions
        Index("ix_applications_user_stage", "user_id", "stage"),
    )
