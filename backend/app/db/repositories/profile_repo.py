from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.profile import Profile


class ProfileRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_for_user(self, *, user_id: UUID) -> Profile | None:
        stmt = select(Profile).where(Profile.user_id == user_id)
        return self.db.scalar(stmt)

    def create(self, *, user_id: UUID) -> Profile:
        profile = Profile(user_id=user_id)
        self.db.add(profile)
        return profile

    def get_or_create_for_user(self, *, user_id: UUID) -> Profile:
        """Find-or-create, same shape as CompanyRepository.get_or_create_for_user:
        flushes (not commits) so the caller gets an id immediately but still
        owns the final commit."""
        existing = self.get_for_user(user_id=user_id)
        if existing:
            return existing

        profile = self.create(user_id=user_id)
        self.db.flush()
        return profile

    def update(self, *, profile: Profile, data: dict) -> None:
        for field, value in data.items():
            setattr(profile, field, value)
