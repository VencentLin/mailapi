from backend.app.db.base import Base
from backend.app.models.enums import MailAccountOwnerType, UserRole


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
