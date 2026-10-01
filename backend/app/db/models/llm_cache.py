from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import utcnow


class LLMCache(Base):
    """Validated LLM results keyed by a hash of everything that determines
    them (operation, prompt version, provider, input). Not user-scoped: the
    same posting text parses to the same result for anyone, and nothing
    user-identifying is stored - only the structured output."""

    __tablename__ = "llm_cache"

    # sha256 hex digest - a natural key, so no surrogate UUID.
    cache_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    operation: Mapped[str] = mapped_column(String(50), nullable=False)
    result: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
