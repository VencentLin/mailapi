from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, quote, urlparse

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.core.crypto import TokenCipher
from backend.app.models.enums import MailAccountOwnerType, MailAccountStatus, UserRole
from backend.app.models.logs import AuditLog, MailAccountClaim, MailFetchLog
from backend.app.models.mail_account import MailAccount
from backend.app.services.users import create_user


def _configure_microsoft_oauth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MICROSOFT_OAUTH_CLIENT_ID", "mailapi-client-id")
    monkeypatch.delenv("MICROSOFT_OAUTH_CLIENT_SECRET", raising=False)
    monkeypatch.setenv(
        "MICROSOFT_OAUTH_REDIRECT_URI",
        "https://mailapi.example.com/api/oauth/microsoft/callback",
    )
    monkeypatch.setenv("MICROSOFT_OAUTH_SCOPES", "offline_access User.Read Mail.Read")
    monkeypatch.setenv("MICROSOFT_OAUTH_TENANT", "consumers")
    monkeypatch.setenv("MICROSOFT_OAUTH_PROMPT", "select_account")
    get_settings.cache_clear()


async def _login_as(
    client: AsyncClient,
    session: AsyncSession,
    username: str,
    role: UserRole,
) -> tuple[int, str]:
    user = await create_user(
        session,
        username=username,
        email=f"{username}@example.com",
        password="pw",
        role=role,
    )
    resp = await client.post("/auth/login", json={"username": username, "password": "pw"})
    assert resp.status_code == 200
    return user.id, resp.json()["access_token"]


async def _create_account(
    session: AsyncSession,
    *,
    email: str,
    owner_type: MailAccountOwnerType,
    owner_user_id: int | None = None,
    refresh_token: str = "stored-rt",
) -> MailAccount:
    cipher = TokenCipher(key=get_settings().token_encryption_key)
    account = MailAccount(
        email=email,
        client_id=f"client-{email}",
        refresh_token_encrypted=cipher.encrypt(refresh_token),
        owner_type=owner_type,
        owner_user_id=owner_user_id,
        status=MailAccountStatus.ACTIVE,
        created_via="test",
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)
    return account


@pytest.mark.asyncio
async def test_admin_can_list_all_mail_accounts_and_filter_by_user(
    client: AsyncClient,
    test_session: AsyncSession,
):
    admin_id, admin_token = await _login_as(client, test_session, "mailadmin", UserRole.ADMIN)
    user_id, _ = await _login_as(client, test_session, "mailuser", UserRole.USER)
    await _create_account(
        test_session,
        email="admin-owned@example.com",
        owner_type=MailAccountOwnerType.USER,
        owner_user_id=admin_id,
    )
    await _create_account(
        test_session,
        email="user-owned@example.com",
        owner_type=MailAccountOwnerType.USER,
        owner_user_id=user_id,
    )
    await _create_account(
        test_session,
        email="public@example.com",
        owner_type=MailAccountOwnerType.PUBLIC,
    )

    all_resp = await client.get(
        "/api/mail-accounts",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert all_resp.status_code == 200
    assert {item["email"] for item in all_resp.json()} == {
        "admin-owned@example.com",
        "user-owned@example.com",
        "public@example.com",
    }

    filtered_resp = await client.get(
        f"/api/mail-accounts?owner_user_id={user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert filtered_resp.status_code == 200
    assert [item["email"] for item in filtered_resp.json()] == ["user-owned@example.com"]


@pytest.mark.asyncio
async def test_regular_user_sees_own_and_public_mail_accounts_only(
    client: AsyncClient,
    test_session: AsyncSession,
):
    owner_id, owner_token = await _login_as(client, test_session, "visibleowner", UserRole.USER)
    other_id, _ = await _login_as(client, test_session, "hiddenowner", UserRole.USER)
    await _create_account(
        test_session,
        email="own@example.com",
        owner_type=MailAccountOwnerType.USER,
        owner_user_id=owner_id,
    )
    await _create_account(
        test_session,
        email="other@example.com",
        owner_type=MailAccountOwnerType.USER,
        owner_user_id=other_id,
    )
    await _create_account(
        test_session,
        email="pool@example.com",
        owner_type=MailAccountOwnerType.PUBLIC,
    )

    resp = await client.get(
        "/api/mail-accounts",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert resp.status_code == 200
    assert {item["email"] for item in resp.json()} == {"own@example.com", "pool@example.com"}


@pytest.mark.asyncio
async def test_user_can_create_owned_mail_account_without_leaking_refresh_token(
    client: AsyncClient,
    test_session: AsyncSession,
):
    user_id, token = await _login_as(client, test_session, "mailcreator", UserRole.USER)

    resp = await client.post(
        "/api/mail-accounts",
        json={
            "email": "new-owned@example.com",
            "client_id": "client-id",
            "refresh_token": "raw-refresh-token",
            "remark": "primary",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "new-owned@example.com"
    assert body["owner_user_id"] == user_id
    assert "refresh_token" not in body

    stored = (
        await test_session.execute(
            select(MailAccount).where(MailAccount.email == "new-owned@example.com")
        )
    ).scalar_one()
    assert "raw-refresh-token" not in stored.refresh_token_encrypted
    assert stored.owner_type == MailAccountOwnerType.USER


@pytest.mark.asyncio
async def test_user_can_claim_public_mail_account(
    client: AsyncClient,
    test_session: AsyncSession,
):
    user_id, token = await _login_as(client, test_session, "claimer", UserRole.USER)
    account = await _create_account(
        test_session,
        email="claimable@example.com",
        owner_type=MailAccountOwnerType.PUBLIC,
    )

    resp = await client.post(
        f"/api/mail-accounts/{account.id}/claim",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    assert resp.json()["owner_user_id"] == user_id

    claim = (await test_session.execute(select(MailAccountClaim))).scalar_one()
    assert claim.mail_account_id == account.id
    assert claim.claimed_by_user_id == user_id


@pytest.mark.asyncio
async def test_admin_can_view_and_update_refresh_token_with_audit_logs(
    client: AsyncClient,
    test_session: AsyncSession,
):
    _, admin_token = await _login_as(client, test_session, "credentialadmin", UserRole.ADMIN)
    account = await _create_account(
        test_session,
        email="credential@example.com",
        owner_type=MailAccountOwnerType.PUBLIC,
        refresh_token="old-refresh",
    )

    view_resp = await client.get(
        f"/api/mail-accounts/{account.id}/credentials",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert view_resp.status_code == 200
    assert view_resp.json()["refresh_token"] == "old-refresh"

    update_resp = await client.patch(
        f"/api/mail-accounts/{account.id}/credentials",
        json={"client_id": "new-client", "refresh_token": "new-refresh"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert update_resp.status_code == 200

    refreshed = await test_session.get(MailAccount, account.id)
    assert refreshed is not None
    assert refreshed.client_id == "new-client"
    cipher = TokenCipher(key=get_settings().token_encryption_key)
    assert cipher.decrypt(refreshed.refresh_token_encrypted) == "new-refresh"

    actions = [
        item.action
        for item in (await test_session.execute(select(AuditLog).order_by(AuditLog.id))).scalars()
    ]
    assert actions == ["mail_account.credentials.view", "mail_account.credentials.update"]


@pytest.mark.asyncio
async def test_regular_user_cannot_view_raw_credentials(
    client: AsyncClient,
    test_session: AsyncSession,
):
    user_id, token = await _login_as(client, test_session, "credentialuser", UserRole.USER)
    account = await _create_account(
        test_session,
        email="private-credential@example.com",
        owner_type=MailAccountOwnerType.USER,
        owner_user_id=user_id,
    )

    resp = await client.get(
        f"/api/mail-accounts/{account.id}/credentials",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_user_can_disable_own_mail_account(
    client: AsyncClient,
    test_session: AsyncSession,
):
    user_id, token = await _login_as(client, test_session, "maildeleter", UserRole.USER)
    account = await _create_account(
        test_session,
        email="disable-me@example.com",
        owner_type=MailAccountOwnerType.USER,
        owner_user_id=user_id,
    )

    resp = await client.delete(
        f"/api/mail-accounts/{account.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 204
    refreshed = await test_session.get(MailAccount, account.id)
    assert refreshed is not None
    assert refreshed.status == MailAccountStatus.DISABLED


@pytest.mark.asyncio
async def test_test_fetch_endpoint_fetches_and_writes_log(
    client: AsyncClient,
    test_session: AsyncSession,
):
    user_id, token = await _login_as(client, test_session, "mailtester", UserRole.USER)
    account = await _create_account(
        test_session,
        email="test-fetch@example.com",
        owner_type=MailAccountOwnerType.USER,
        owner_user_id=user_id,
    )

    with patch(
        "backend.app.api.routes.mail_accounts.fetch_messages",
        new=AsyncMock(return_value=([{"id": "m1", "subject": "Hi"}], "graph")),
    ):
        resp = await client.post(
            f"/api/mail-accounts/{account.id}/test-fetch",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    assert resp.json()["protocol"] == "graph"
    log = (await test_session.execute(select(MailFetchLog))).scalar_one()
    assert log.operation == "test_fetch"
    assert log.status == "success"


@pytest.mark.asyncio
async def test_import_mail_accounts_accepts_delimited_format_and_ignores_password(
    client: AsyncClient,
    test_session: AsyncSession,
):
    user_id, token = await _login_as(client, test_session, "mailimporter", UserRole.USER)

    resp = await client.post(
        "/api/mail-accounts/import",
        json={
            "text": "\n".join(
                [
                    " FirstImport@outlook.com ----secret-password----client-1----refresh-1",
                    "secondimport@outlook.com----another-password----client-2----refresh-2----tail",
                ]
            )
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["created"] == 2
    assert body["skipped"] == 0
    assert body["failed"] == 0

    accounts = (
        await test_session.execute(
            select(MailAccount).where(
                MailAccount.email.in_(
                    ["firstimport@outlook.com", "secondimport@outlook.com"]
                )
            )
        )
    ).scalars().all()
    assert {account.owner_user_id for account in accounts} == {user_id}
    assert {account.owner_type for account in accounts} == {MailAccountOwnerType.USER}

    cipher = TokenCipher(key=get_settings().token_encryption_key)
    tokens_by_email = {
        account.email: cipher.decrypt(account.refresh_token_encrypted)
        for account in accounts
    }
    assert tokens_by_email["firstimport@outlook.com"] == "refresh-1"
    assert tokens_by_email["secondimport@outlook.com"] == "refresh-2----tail"
    assert "secret-password" not in "\n".join(
        account.refresh_token_encrypted for account in accounts
    )


@pytest.mark.asyncio
async def test_import_mail_accounts_reports_existing_duplicates_and_invalid_lines(
    client: AsyncClient,
    test_session: AsyncSession,
):
    _, token = await _login_as(client, test_session, "mailimporter2", UserRole.USER)
    await _create_account(
        test_session,
        email="existing-import@example.com",
        owner_type=MailAccountOwnerType.PUBLIC,
    )

    resp = await client.post(
        "/api/mail-accounts/import",
        json={
            "text": "\n".join(
                [
                    "existing-import@example.com----pw----client-existing----refresh-existing",
                    "new-import@example.com----pw----client-new----refresh-new",
                    "NEW-import@example.com----pw----client-dup----refresh-dup",
                    "bad-line-without-delimiters",
                    "not-an-email----pw----client-bad----refresh-bad",
                ]
            )
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["created"] == 1
    assert body["skipped"] == 2
    assert body["failed"] == 2
    assert [item["status"] for item in body["items"]] == [
        "skipped",
        "created",
        "skipped",
        "failed",
        "failed",
    ]


@pytest.mark.asyncio
async def test_admin_can_import_mail_accounts_to_public_pool(
    client: AsyncClient,
    test_session: AsyncSession,
):
    _, token = await _login_as(client, test_session, "adminimporter", UserRole.ADMIN)

    resp = await client.post(
        "/api/mail-accounts/import",
        json={
            "owner_type": "public",
            "text": "public-import@example.com----pw----client-public----refresh-public",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    assert resp.json()["created"] == 1

    account = (
        await test_session.execute(
            select(MailAccount).where(MailAccount.email == "public-import@example.com")
        )
    ).scalar_one()
    assert account.owner_type == MailAccountOwnerType.PUBLIC
    assert account.owner_user_id is None
    assert account.created_via == "admin_import"


@pytest.mark.asyncio
async def test_user_can_create_reauthorize_url_for_own_mail_account(
    client: AsyncClient,
    test_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    _configure_microsoft_oauth(monkeypatch)
    user_id, token = await _login_as(client, test_session, "reauthowner", UserRole.USER)
    account = await _create_account(
        test_session,
        email="reauth-owner@outlook.com",
        owner_type=MailAccountOwnerType.USER,
        owner_user_id=user_id,
    )

    resp = await client.post(
        f"/api/mail-accounts/{account.id}/reauthorize-url",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["expires_in"] == 600
    parsed = urlparse(body["auth_url"])
    params = parse_qs(parsed.query)
    assert parsed.scheme == "https"
    assert parsed.netloc == "login.microsoftonline.com"
    assert parsed.path == "/consumers/oauth2/v2.0/authorize"
    assert params["client_id"] == ["mailapi-client-id"]
    assert params["response_type"] == ["code"]
    assert params["redirect_uri"] == [
        "https://mailapi.example.com/api/oauth/microsoft/callback"
    ]
    assert params["response_mode"] == ["query"]
    assert params["scope"] == ["offline_access User.Read Mail.Read"]
    assert params["login_hint"] == ["reauth-owner@outlook.com"]
    assert params["prompt"] == ["select_account"]
    assert params["state"][0]


@pytest.mark.asyncio
async def test_microsoft_callback_updates_mail_account_refresh_token(
    client: AsyncClient,
    test_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    _configure_microsoft_oauth(monkeypatch)
    user_id, token = await _login_as(client, test_session, "reauthcallback", UserRole.USER)
    account = await _create_account(
        test_session,
        email="reauth-callback@outlook.com",
        owner_type=MailAccountOwnerType.USER,
        owner_user_id=user_id,
        refresh_token="old-refresh",
    )
    account.status = MailAccountStatus.INVALID
    account.last_error_code = "oauth_invalid_grant"
    await test_session.commit()

    url_resp = await client.post(
        f"/api/mail-accounts/{account.id}/reauthorize-url",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert url_resp.status_code == 200
    state = parse_qs(urlparse(url_resp.json()["auth_url"]).query)["state"][0]

    with (
        patch(
            "backend.app.api.routes.oauth.MicrosoftOAuthClient.exchange_code",
            new=AsyncMock(
                return_value=SimpleNamespace(
                    access_token="new-access-token",
                    refresh_token="new-refresh-token",
                )
            ),
        ),
        patch(
            "backend.app.api.routes.oauth.MicrosoftOAuthClient.fetch_profile_email",
            new=AsyncMock(return_value="reauth-callback@outlook.com"),
        ),
    ):
        callback_resp = await client.get(
            f"/api/oauth/microsoft/callback?code=auth-code&state={quote(state, safe='')}",
            follow_redirects=False,
        )

    assert callback_resp.status_code in {302, 307}
    assert callback_resp.headers["location"].startswith(
        "/mail-accounts?reauthorize=success&email=reauth-callback%40outlook.com"
    )

    refreshed = await test_session.get(MailAccount, account.id)
    assert refreshed is not None
    assert refreshed.client_id == "mailapi-client-id"
    assert refreshed.status == MailAccountStatus.ACTIVE
    assert refreshed.last_error_code is None
    cipher = TokenCipher(key=get_settings().token_encryption_key)
    assert cipher.decrypt(refreshed.refresh_token_encrypted) == "new-refresh-token"

    audit = (await test_session.execute(select(AuditLog))).scalar_one()
    assert audit.action == "mail_account.credentials.reauthorize"
    assert audit.actor_user_id == user_id
    assert audit.target_id == str(account.id)


@pytest.mark.asyncio
async def test_microsoft_callback_rejects_mismatched_profile_email(
    client: AsyncClient,
    test_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    _configure_microsoft_oauth(monkeypatch)
    user_id, token = await _login_as(client, test_session, "reauthmismatch", UserRole.USER)
    account = await _create_account(
        test_session,
        email="expected-mailbox@outlook.com",
        owner_type=MailAccountOwnerType.USER,
        owner_user_id=user_id,
        refresh_token="old-refresh",
    )
    url_resp = await client.post(
        f"/api/mail-accounts/{account.id}/reauthorize-url",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert url_resp.status_code == 200
    state = parse_qs(urlparse(url_resp.json()["auth_url"]).query)["state"][0]

    with (
        patch(
            "backend.app.api.routes.oauth.MicrosoftOAuthClient.exchange_code",
            new=AsyncMock(
                return_value=SimpleNamespace(
                    access_token="new-access-token",
                    refresh_token="wrong-mailbox-refresh",
                )
            ),
        ),
        patch(
            "backend.app.api.routes.oauth.MicrosoftOAuthClient.fetch_profile_email",
            new=AsyncMock(return_value="other-mailbox@outlook.com"),
        ),
    ):
        callback_resp = await client.get(
            f"/api/oauth/microsoft/callback?code=auth-code&state={quote(state, safe='')}",
            follow_redirects=False,
        )

    assert callback_resp.status_code in {302, 307}
    assert callback_resp.headers["location"].startswith(
        "/mail-accounts?reauthorize=failed&reason=email_mismatch"
    )

    refreshed = await test_session.get(MailAccount, account.id)
    assert refreshed is not None
    cipher = TokenCipher(key=get_settings().token_encryption_key)
    assert cipher.decrypt(refreshed.refresh_token_encrypted) == "old-refresh"
