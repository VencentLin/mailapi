from pydantic import BaseModel, EmailStr, Field

from backend.app.models.enums import UserRole, UserStatus


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.USER
    status: UserStatus = UserStatus.ACTIVE


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=2, max_length=64)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=6)
    role: UserRole | None = None
    status: UserStatus | None = None
