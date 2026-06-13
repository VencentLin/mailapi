from enum import StrEnum

from sqlalchemy import Enum as SqlEnum


def string_enum[T: StrEnum](enum_cls: type[T]) -> SqlEnum:
    return SqlEnum(
        enum_cls,
        values_callable=lambda cls: [member.value for member in cls],
        native_enum=False,
        validate_strings=True,
    )


class UserRole(StrEnum):
    ADMIN = "admin"
    USER = "user"


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class ApiKeyStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    EXPIRED = "expired"


class MailAccountOwnerType(StrEnum):
    USER = "user"
    PUBLIC = "public"


class MailAccountStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    INVALID = "invalid"
