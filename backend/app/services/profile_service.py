from uuid import UUID

from sqlalchemy.orm import Session

from app.api.schemas.profile import ProfileUpdate
from app.db.repositories.profile_repo import ProfileRepository


class ProfileService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = ProfileRepository(db)

    def get_or_create_profile_for_user(self, *, user_id: UUID):
        profile = self.repository.get_or_create_for_user(user_id=user_id)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def update_profile(self, *, user_id: UUID, payload: ProfileUpdate):
        profile = self.repository.get_or_create_for_user(user_id=user_id)

        # model_dump() recursively dumps nested BaseModels (LanguageEntry)
        # to plain dicts, which is what the JSONB column expects.
        data = payload.model_dump(exclude_unset=True)

        self.repository.update(profile=profile, data=data)
        self.db.commit()
        self.db.refresh(profile)
        return profile
