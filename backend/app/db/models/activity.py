from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin
from app.domain.enums import ActivityType
from app.db.mixins import utcnow


class Activity(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "activities"

    application_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    activity_type: Mapped[ActivityType] = mapped_column(
        Enum(ActivityType, name="activity_type"),
        nullable=False,
    )

    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )
    # DOMAIN: when the event happened (user can put historical date)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )

    application = relationship("Application", back_populates="activities")

    __table_args__ = (
        Index(
            "ix_activities_application_occurred_at",
            "application_id",
            occurred_at.desc(),
        ),
    )
