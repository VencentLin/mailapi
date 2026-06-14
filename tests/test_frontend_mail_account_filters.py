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


def test_regular_mail_account_view_defaults_to_own_mailboxes_and_can_show_public_pool() -> None:
    source = MAIL_ACCOUNT_VIEW.read_text(encoding="utf-8")

    assert "filters.owner_type = 'user'" in source
    assert "filters.owner_user_id = auth.userId" in source
    assert "v-if=\"!auth.isAdmin\"" in source
    assert "公共池" in source


def test_mail_account_create_and_import_use_current_user_without_user_id_input() -> None:
    source = MAIL_ACCOUNT_VIEW.read_text(encoding="utf-8")

    assert 'label="用户 ID"' not in source
    assert "createForm.owner_user_id = auth.userId" in source
    assert "importForm.owner_user_id = auth.userId" in source
    assert "v-model=\"createForm.owner_user_id\"" in source
    assert "v-model=\"importForm.owner_user_id\"" in source
