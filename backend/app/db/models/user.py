from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin, TimestampMixin

class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(320),
        unique=True,
        index=True,
        nullable=False,
    )

    cognito_sub: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        index=True,
        nullable=False,
    )

    applications = relationship(
        "Application",
        back_populates="user",
        cascade="all, delete-orphan",
    )
