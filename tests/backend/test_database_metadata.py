from backend.app.db.base import Base
from backend.app.models.api_key import ApiKey
from backend.app.models.enums import MailAccountOwnerType, UserRole
from backend.app.models.mail_account import MailAccount
from backend.app.models.user import User


def test_foundation_tables_are_registered():
    expected_tables = {
        "users",
        "api_keys",
        "mail_accounts",
        "mail_account_claims",
        "mail_fetch_logs",
        "audit_logs",
    }

    assert expected_tables.issubset(set(Base.metadata.tables))


def test_core_enum_values_match_design_doc():
    assert UserRole.ADMIN.value == "admin"
    assert UserRole.USER.value == "user"
    assert MailAccountOwnerType.USER.value == "user"
    assert MailAccountOwnerType.PUBLIC.value == "public"


def test_enum_columns_use_string_values_not_native_postgres_enums():
    enum_columns = [
        User.__table__.c.role,
        User.__table__.c.status,
        ApiKey.__table__.c.status,
        MailAccount.__table__.c.owner_type,
        MailAccount.__table__.c.status,
    ]

    for column in enum_columns:
        assert column.type.native_enum is False
        assert all(value == value.lower() for value in column.type.enums)
