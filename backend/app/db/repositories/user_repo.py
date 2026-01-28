from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_cognito_sub(self, *, cognito_sub: UUID) -> User | None:
        stmt = select(User).where(User.cognito_sub == cognito_sub)
        return self.db.scalar(stmt)

    def create(self, *, cognito_sub: UUID, email: str | None) -> User:
        user = User(cognito_sub=cognito_sub, email=email)
        self.db.add(user)
        return user

    def get_or_create(self, *, cognito_sub: UUID, email: str | None) -> User:
        user = self.get_by_cognito_sub(cognito_sub=cognito_sub)
        if user:
            if user.email is None and email is not None:
                user.email = email
            return user

        return self.create(cognito_sub=cognito_sub, email=email)
