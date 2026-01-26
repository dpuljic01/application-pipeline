from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr

class UserRead(BaseModel):
    id: UUID
    email: EmailStr
    created_at: datetime
    updated_at: datetime
