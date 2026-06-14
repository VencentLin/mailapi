from pathlib import Path

MAIL_ACCOUNT_VIEW = Path("frontend/src/views/mail/MailAccountListView.vue")
FILTER_BUTTON = '<el-button type="primary" :icon="Search" @click="loadAccounts">筛选</el-button>'


def test_admin_mail_account_view_defaults_to_current_admin_owner_filter() -> None:
    source = MAIL_ACCOUNT_VIEW.read_text(encoding="utf-8")

    assert "filters.owner_user_id = auth.userId" in source


def test_mail_account_filters_auto_reload_without_filter_button() -> None:
    source = MAIL_ACCOUNT_VIEW.read_text(encoding="utf-8")

    assert "watch(" in source
    assert "loadAccountsDebounced" in source
    assert FILTER_BUTTON not in source
