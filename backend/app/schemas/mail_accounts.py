from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from backend.app.models.enums import MailAccountOwnerType, MailAccountStatus


class MailAccountResolve(BaseModel):
    """Input for resolving / creating a mail account."""

    email: str
    client_id: str = ""
    refresh_token: str = ""


class MailAccountResolved(BaseModel):
    """Result of resolving a mail account — includes the account model and creation flag."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    account: object  # MailAccount ORM instance
    created: bool


class MailAccountPublic(BaseModel):
    id: int
    email: EmailStr
    client_id: str
    owner_type: MailAccountOwnerType
    owner_user_id: int | None
    status: MailAccountStatus
    default_proxy: str | None
    last_protocol: str | None
    last_success_at: datetime | None
    last_error_code: str | None
    remark: str | None
    created_by_user_id: int | None
    created_via: str
    created_at: datetime
    updated_at: datetime
    can_claim: bool = False
    can_view_credentials: bool = False


class MailAccountCreate(BaseModel):
    email: EmailStr
    client_id: str = Field(min_length=1, max_length=255)
    refresh_token: str = Field(min_length=1)
    owner_type: MailAccountOwnerType | None = None
    owner_user_id: int | None = None
    status: MailAccountStatus = MailAccountStatus.ACTIVE
    default_proxy: str | None = Field(default=None, max_length=512)
    remark: str | None = Field(default=None, max_length=500)


class MailAccountUpdate(BaseModel):
    owner_type: MailAccountOwnerType | None = None
    owner_user_id: int | None = None
    status: MailAccountStatus | None = None
    default_proxy: str | None = Field(default=None, max_length=512)
    remark: str | None = Field(default=None, max_length=500)


class MailAccountCredentialsPublic(BaseModel):
    client_id: str
    refresh_token: str


class MailAccountCredentialsUpdate(BaseModel):
    client_id: str | None = Field(default=None, min_length=1, max_length=255)
    refresh_token: str | None = Field(default=None, min_length=1)


class MailAccountTestFetchResponse(BaseModel):
    code: str = "200"
    protocol: str
    message_count: int
    trace_id: str
