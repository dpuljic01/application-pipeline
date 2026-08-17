from uuid import UUID
from sqlalchemy.orm import Session

from app.db.models.user import User
from app.db.repositories.user_repo import UserRepository


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = UserRepository(db)

    def get_or_create_current_user(
        self, *, cognito_sub: UUID, email: str | None
    ) -> User:
        user = self.repository.get_or_create(cognito_sub=cognito_sub, email=email)
        self.db.commit()
        self.db.refresh(user)
        return user
