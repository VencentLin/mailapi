from pathlib import Path

LOGIN_VIEW = Path("frontend/src/views/LoginView.vue")
USER_LIST_VIEW = Path("frontend/src/views/users/UserListView.vue")
AUTH_API = Path("frontend/src/api/auth.ts")
USERS_API = Path("frontend/src/api/users.ts")
API_USAGE_VIEW = Path("frontend/src/views/docs/ApiUsageView.vue")


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


def test_user_management_view_can_delete_users() -> None:
    source = USER_LIST_VIEW.read_text(encoding="utf-8")
    api_source = USERS_API.read_text(encoding="utf-8")

    assert "deleteUser" in api_source
    assert "handleDeleteUser" in source
    assert "删除" in source
    assert "delete<void>(`/api/users/${userId}`" in api_source


def test_api_usage_ai_guide_uses_current_origin_and_current_user_api() -> None:
    source = API_USAGE_VIEW.read_text(encoding="utf-8")

    assert "window.location.origin" in source
    assert "MAILAPI_BASE_URL：${serviceBaseUrl.value}" in source
    assert "DELETE /api/users/{id}" in source
    assert "http://127.0.0.1:8000 或云端地址" not in source
