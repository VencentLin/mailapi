from pydantic import BaseModel, EmailStr

from backend.app.models.enums import UserRole, UserStatus


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.USER
    status: UserStatus = UserStatus.ACTIVE
