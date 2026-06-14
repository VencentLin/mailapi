from pathlib import Path

LOGIN_VIEW = Path("frontend/src/views/LoginView.vue")
USER_LIST_VIEW = Path("frontend/src/views/users/UserListView.vue")
AUTH_API = Path("frontend/src/api/auth.ts")
USERS_API = Path("frontend/src/api/users.ts")


def test_login_view_exposes_self_registration_pending_admin_review() -> None:
    source = LOGIN_VIEW.read_text(encoding="utf-8")
    api_source = AUTH_API.read_text(encoding="utf-8")

    assert "handleRegister" in source
    assert "注册成功，请等待管理员审核激活后登录" in source
    assert "register(" in api_source
    assert "'/auth/register'" in api_source


def test_user_management_view_can_edit_and_toggle_accounts() -> None:
    source = USER_LIST_VIEW.read_text(encoding="utf-8")
    api_source = USERS_API.read_text(encoding="utf-8")

    assert "updateUser" in source
    assert "handleToggleStatus" in source
    assert "编辑用户" in source
    assert "启用" in source
    assert "停用" in source
    assert "patch<UserPublic>(`/api/users/${userId}`" in api_source
