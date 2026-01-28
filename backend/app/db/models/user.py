from sqlalchemy import UUID, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from uuid import UUID as PyUUID
from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin, TimestampMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str | None] = mapped_column(
        String(320),
        unique=True,
        index=True,
        nullable=True,
    )

    cognito_sub: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        unique=True,
    )

    applications = relationship(
        "Application",
        back_populates="user",
        cascade="all, delete-orphan",
    )
