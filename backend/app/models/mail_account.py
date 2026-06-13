from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin
from backend.app.models.enums import MailAccountOwnerType, MailAccountStatus


class MailAccount(TimestampMixin, Base):
    __tablename__ = "mail_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    refresh_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    owner_type: Mapped[MailAccountOwnerType] = mapped_column(
        Enum(MailAccountOwnerType),
        nullable=False,
        index=True,
    )
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[MailAccountStatus] = mapped_column(Enum(MailAccountStatus), nullable=False)
    default_proxy: Mapped[str | None] = mapped_column(String(512))
    last_protocol: Mapped[str | None] = mapped_column(String(32))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String(80))
    remark: Mapped[str | None] = mapped_column(String(500))
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_via: Mapped[str] = mapped_column(String(40), nullable=False)

    owner_user = relationship("User", foreign_keys=[owner_user_id], back_populates="mail_accounts")
