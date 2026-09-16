from uuid import UUID as PyUUID

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Profile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "profiles"

    # One profile per user - unique, not just indexed, so the DB itself
    # enforces the 1:1 relationship (see ProfileRepository.get_or_create_for_user).
    user_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # All personal-data fields are nullable with no server-side defaults:
    # a freshly auto-created profile is empty, never seeded with anyone's
    # real data. The user fills this in themselves via the Profile page.
    years_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    skills: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    languages: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    target_seniorities: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )
    min_salary_chf: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ideal_salary_chf: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Free text, used only as LLM context for flagging commute concerns -
    # never parsed or geocoded (see services/matcher.py).
    home_location: Mapped[str | None] = mapped_column(String(120), nullable=True)
