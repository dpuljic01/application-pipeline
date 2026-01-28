from datetime import datetime

from sqlalchemy import String, DateTime, Enum, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin, TimestampMixin
from app.domain.enums import ApplicationStage


class Application(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "applications"

    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    company: Mapped[str] = mapped_column(String(200), nullable=False)
    role_title: Mapped[str] = mapped_column(String(128), nullable=False)
    job_url: Mapped[str | None] = mapped_column(String(2000))
    location: Mapped[str | None] = mapped_column(String(100))
    salary_range: Mapped[str | None] = mapped_column(String(100))
    stage: Mapped[ApplicationStage] = mapped_column(
        Enum(ApplicationStage, name="application_stage"),
        nullable=False,
        default=ApplicationStage.SAVED,
    )

    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stage_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user = relationship("User", back_populates="applications")
    activities = relationship(
        "Activity",
        back_populates="application",
        cascade="all, delete-orphan",  # propagate operations from parent, delete-orphan to remove unlinked activities
    )


Index(
    "ix_applications_user_last_activity",
    Application.user_id,
    Application.last_activity_at.desc(),
)
Index(
    "ix_applications_user_stage",
    Application.user_id,
    Application.stage,
)
