from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin
from backend.app.models.enums import UserRole, UserStatus, string_enum


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(string_enum(UserRole), nullable=False)
    status: Mapped[UserStatus] = mapped_column(string_enum(UserStatus), nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    api_keys = relationship("ApiKey", back_populates="user")
    mail_accounts = relationship(
        "MailAccount",
        foreign_keys="MailAccount.owner_user_id",
        back_populates="owner_user",
    )
