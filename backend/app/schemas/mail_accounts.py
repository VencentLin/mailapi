from pydantic import BaseModel, ConfigDict


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
