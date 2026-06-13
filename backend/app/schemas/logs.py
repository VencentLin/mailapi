from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MailFetchLogPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trace_id: str
    user_id: int | None
    api_key_id: int | None
    mail_account_id: int | None
    email: str
    mailbox: str
    operation: str
    source_protocol: str | None
    status: str
    error_code: str | None
    error_message: str | None
    duration_ms: int | None
    created_at: datetime
    updated_at: datetime


class AuditLogPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_user_id: int | None
    action: str
    target_type: str
    target_id: str
    metadata_json: dict | None
    ip_address: str | None
    created_at: datetime
    updated_at: datetime
